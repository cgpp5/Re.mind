import csv
import json
import os
import re
import html
import hashlib
from pathlib import Path
from datetime import datetime

# ==========================================
# REGISTRY MANAGEMENT
# ==========================================

def get_file_hash(file_path):
    """Calculates the SHA-256 hash of a file to detect changes."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_content_hash(content_str):
    """Calculates the SHA-256 hash of a string (session content)."""
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest()

def load_registry(registry_path):
    """Loads the import registry to prevent duplicate processing."""
    if registry_path.exists():
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Migrate from old v1 format to v2 format if needed
                if "files" not in data:
                    return {"files": data, "sessions": {}}
                return data
        except json.JSONDecodeError:
            pass
    return {"files": {}, "sessions": {}}

def save_registry(registry_path, registry_data):
    """Saves the updated import registry."""
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry_data, f, indent=2)

# ==========================================
# HTML TO MARKDOWN CONVERTER
# ==========================================

def clean_html_to_markdown(html_content):
    """
    Converts advanced HTML formatting from Gemini's JSON into Markdown.
    Preserves headings, lists, tables, and inline formatting without external dependencies.
    """
    text = html_content
    
    # 1. Handle Headings
    text = re.sub(r'<h[1-2]\b[^>]*>(.*?)</h[1-2]>', r'\n## \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h3\b[^>]*>(.*?)</h3>', r'\n### \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h[4-6]\b[^>]*>(.*?)</h[4-6]>', r'\n#### \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Handle block elements (paragraphs, dividers and line breaks)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<hr\s*/?>', '\n---\n\n', text, flags=re.IGNORECASE)
    
    # 3. Handle Lists
    text = re.sub(r'<li\b[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<ul\b[^>]*>|<ol\b[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</ul>|</ol>', '\n', text, flags=re.IGNORECASE)
    
    # 4. Handle Tables (Transforms to pipe-separated rows for readability)
    text = re.sub(r'<table\b[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</table>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<tr\b[^>]*>', '| ', text, flags=re.IGNORECASE)
    text = re.sub(r'</tr>', ' |\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<td\b[^>]*>|<th\b[^>]*>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'</td>|</th>', ' |', text, flags=re.IGNORECASE)
    text = re.sub(r'<thead\b[^>]*>|</thead>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<tbody\b[^>]*>|</tbody>', '', text, flags=re.IGNORECASE)
    
    # 5. Handle code blocks (<pre><code>...</code></pre>)
    text = re.sub(r'<pre><code[^>]*>', '\n```\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</code></pre>', '\n```\n', text, flags=re.IGNORECASE)
    
    # 6. Handle inline formatting
    text = re.sub(r'<b\b[^>]*>|</b>|<strong\b[^>]*>|</strong>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'<i\b[^>]*>|</i>|<em\b[^>]*>|</em>', '*', text, flags=re.IGNORECASE)
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.IGNORECASE | re.DOTALL)
    
    # 7. Strip all remaining / unsupported HTML tags safely
    text = re.sub(r'<[^>]+>', '', text)
    
    # 8. Unescape HTML entities (e.g., &lt; to <, &amp; to &)
    text = html.unescape(text)
    
    # 9. Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

# ==========================================
# FILE PARSING & EXTRACTION
# ==========================================

def detect_csv_columns(headers):
    """
    Attempts to guess the correct columns based on common export names.
    Includes explicit conversation detection for tools like GitHub Copilot.
    """
    headers_lower = [h.lower() for h in headers]
    col_map = {'date': None, 'author': None, 'message': None, 'conversation': None}
    
    for col in ['date', 'timestamp', 'time', 'created_at']:
        if col in headers_lower: col_map['date'] = headers[headers_lower.index(col)]; break
            
    for col in ['role', 'sender', 'author', 'user']:
        if col in headers_lower: col_map['author'] = headers[headers_lower.index(col)]; break
            
    for col in ['content', 'message', 'text', 'completion']:
        if col in headers_lower: col_map['message'] = headers[headers_lower.index(col)]; break
            
    for col in ['conversation', 'thread', 'chat', 'topic']:
        if col in headers_lower: col_map['conversation'] = headers[headers_lower.index(col)]; break
            
    return col_map

def extract_rows_from_csv(file_path):
    """Extracts standard rows from a CSV file."""
    rows = []
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        if not headers: return []
        
        col_map = detect_csv_columns(headers)
        if not col_map['message']: return []
        
        for row in reader:
            rows.append({
                'date': row.get(col_map['date'], ''),
                'author': row.get(col_map['author'], 'Unknown') if col_map['author'] else 'Message',
                'message': row.get(col_map['message'], ''),
                'conversation': row.get(col_map['conversation'], '').strip() if col_map['conversation'] else None
            })
    return rows

def extract_rows_from_json(file_path):
    """
    Extracts standard rows from JSON exports (supports Google Gemini and Anthropic Claude).
    Translates their respective structures into user/AI chat turns,
    and converts advanced HTML payloads into structured Markdown when needed.
    """
    rows = []
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        try:
            data = json.load(f)
            if not isinstance(data, list) or len(data) == 0:
                return []
            
            first_item = data[0]
            is_claude = 'chat_messages' in first_item or 'uuid' in first_item
            is_chatgpt = 'mapping' in first_item and 'title' in first_item
            
            if is_claude:
                # --- CLAUDE EXPORT LOGIC ---
                for conv in data:
                    conv_name = conv.get('name', '').strip()
                    if not conv_name:
                        conv_name = f"Claude_Session_{conv.get('created_at', '')[:10]}"
                        
                    messages = conv.get('chat_messages', [])
                    if not isinstance(messages, list):
                        continue
                        
                    for msg in messages:
                        if not isinstance(msg, dict):
                            continue
                            
                        # Role translation
                        sender = msg.get('sender', 'Unknown')
                        if sender == 'human':
                            author = 'User'
                        elif sender == 'assistant':
                            author = 'Claude'
                        else:
                            author = sender.capitalize()
                            
                        # Extract the actual text
                        text = msg.get('text', '')
                        
                        # Sometimes content is formatted as an array of blocks 
                        if not text and isinstance(msg.get('content'), list):
                            parts = []
                            for block in msg['content']:
                                if isinstance(block, dict) and block.get('type') == 'text':
                                    parts.append(block.get('text', ''))
                            text = '\n\n'.join(parts)
                            
                        if not text.strip():
                            continue
                            
                        time_str = msg.get('created_at', conv.get('created_at', ''))
                        
                        rows.append({
                            'date': time_str,
                            'author': author,
                            'message': text.strip(),
                            'conversation': conv_name # Explicit conversation ID!
                        })
            elif is_chatgpt:
                # --- CHATGPT EXPORT LOGIC ---
                for conv in data:
                    conv_name = conv.get('title')
                    if not conv_name:
                        create_time = conv.get('create_time', 0)
                        if create_time:
                            dt = datetime.utcfromtimestamp(create_time)
                            conv_name = f"ChatGPT_Session_{dt.strftime('%Y-%m-%d')}"
                        else:
                            conv_name = "ChatGPT_Session_Unknown"
                            
                    mapping = conv.get('mapping', {})
                    current_node = conv.get('current_node')
                    
                    if not current_node or not mapping:
                        continue
                        
                    # Reconstruct path from current_node backwards
                    path_nodes = []
                    n = current_node
                    while n:
                        node = mapping.get(n)
                        if not node:
                            break
                        msg = node.get('message')
                        if msg:
                            path_nodes.append(msg)
                        n = node.get('parent')
                        
                    # Reverse to chronological order
                    path_nodes.reverse()
                    
                    for msg in path_nodes:
                        author_info = msg.get('author', {})
                        author_role = author_info.get('role', 'unknown')
                        
                        if author_role == 'system':
                            continue
                            
                        if author_role == 'user':
                            author = 'User'
                        elif author_role == 'assistant':
                            author = 'ChatGPT'
                        elif author_role == 'tool':
                            author = 'Tool'
                        else:
                            author = author_role.capitalize()
                            
                        content = msg.get('content', {})
                        parts = content.get('parts', [])
                        
                        text_parts = []
                        for p in parts:
                            if isinstance(p, str):
                                text_parts.append(p)
                            elif isinstance(p, dict):
                                part_type = p.get('content_type', '')
                                if part_type:
                                    text_parts.append(f"*[Attachment: {part_type}]*")
                                    
                        if not text_parts and isinstance(content.get('text'), str):
                            text_parts.append(content['text'])
                            
                        text = '\n\n'.join(text_parts).strip()
                        # Clean up ChatGPT internal filecite/search markers (Private Use Area characters)
                        text = re.sub(r'\ue200.*?\ue201', '', text)
                        
                        if not text:
                            continue
                            
                        msg_time = msg.get('create_time')
                        if msg_time:
                            dt = datetime.utcfromtimestamp(msg_time)
                            time_str = dt.isoformat() + 'Z'
                        else:
                            time_str = ''
                            
                        rows.append({
                            'date': time_str,
                            'author': author,
                            'message': text,
                            'conversation': conv_name
                        })
            else:
                # --- GEMINI EXPORT LOGIC ---
                for item in data:
                    time_str = item.get('time', '')
                    
                    # Extract User Prompt
                    title = item.get('title', '')
                    user_msg = ""
                    if title:
                        # Clean up Google's automated prefixes
                        title = re.sub(r'^(Said |Has dicho:\s*|Has conversado con Gemini\s*|Hiciste la petición\s*)', '', title, flags=re.IGNORECASE)
                        user_msg = html.unescape(title).strip()
                    
                    # Extract AI Response
                    ai_msg = ""
                    safe_html = item.get('safeHtmlItem', [])
                    
                    # 1. Try safeHtmlItem first (holds most of the rich text/HTML responses)
                    if safe_html and isinstance(safe_html, list):
                        raw_html_parts = []
                        for sh_item in safe_html:
                            if isinstance(sh_item, dict) and 'html' in sh_item:
                                raw_html_parts.append(sh_item['html'])
                        
                        if raw_html_parts:
                            raw_html = "\n\n".join(raw_html_parts)
                            ai_msg = clean_html_to_markdown(raw_html)
                        
                    subtitles = item.get('subtitles', [])
                    
                    # 2. Fallback to subtitles (sometimes used for shorter or older responses)
                    if not ai_msg.strip():
                        if subtitles and isinstance(subtitles, list):
                            raw_subtitle = "\n\n".join([sub.get('name', '') for sub in subtitles if isinstance(sub, dict) and sub.get('name')])
                            ai_msg = html.unescape(raw_subtitle)
                    else:
                        # If AI response was in safeHtmlItem, subtitles often hold user attachments!
                        if subtitles and isinstance(subtitles, list):
                            attachment_texts = []
                            for sub in subtitles:
                                name = sub.get('name', '')
                                url = sub.get('url', '')
                                if name:
                                    # Standardize the attachment message
                                    name = re.sub(r'^(Adjuntaste \d+ archivos?\.?)', 'Attached file(s):', name, flags=re.IGNORECASE)
                                    if url:
                                        attachment_texts.append(f"[{name}]({url})")
                                    else:
                                        attachment_texts.append(name)
                            
                            if attachment_texts:
                                attachments_str = " | ".join(attachment_texts)
                                if user_msg:
                                    user_msg += f"\n\n*( {attachments_str} )*"
                                else:
                                    user_msg = f"*( {attachments_str} )*"
                            
                    if user_msg:
                        rows.append({
                            'date': time_str,
                            'author': 'User',
                            'message': user_msg,
                            'conversation': None 
                        })
                    
                    if ai_msg.strip():
                        rows.append({
                            'date': time_str,
                            'author': 'Gemini',
                            'message': ai_msg.strip(),
                            'conversation': None
                        })
        except json.JSONDecodeError:
            print(f"  [!] [{Path(file_path).name}] Invalid JSON format.")
    return rows

def safe_parse_date(date_str):
    """Parses ISO dates safely and strips timezone info."""
    if not date_str: return None
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.replace(tzinfo=None)
    except ValueError:
        return None

# ==========================================
# PROCESSING & MARKDOWN GENERATION
# ==========================================

def process_file_to_markdown(file_path, output_dir, session_registry):
    """
    Reads a file (CSV or JSON), sorts chronologically, and applies
    dual-heuristic grouping (Explicit ID or Time-gap) to generate Markdown.
    Checks session_registry to avoid exporting duplicate sessions.
    """
    input_path = Path(file_path)
    output_path = Path(output_dir)
    
    if input_path.suffix.lower() == '.csv':
        rows = extract_rows_from_csv(input_path)
    elif input_path.suffix.lower() == '.json':
        rows = extract_rows_from_json(input_path)
    else:
        return

    if not rows:
        print(f"  [!] [{input_path.name}] Could not extract valid messages.")
        return

    rows.sort(key=lambda r: safe_parse_date(r['date']) or datetime.min)

    sessions = {}
    current_session_id = "Session_Unknown"
    last_time = None
    SESSION_GAP_HOURS = 8  

    for row in rows:
        conv_name = row.get('conversation')
        row_time = safe_parse_date(row['date'])

        if conv_name:
            session_key = conv_name
        else:
            if row_time:
                if not last_time:
                    current_session_id = f"Session_{row_time.strftime('%Y%m%d_%H%M')}"
                else:
                    diff = row_time - last_time
                    if diff.total_seconds() > (SESSION_GAP_HOURS * 3600):
                        current_session_id = f"Session_{row_time.strftime('%Y%m%d_%H%M')}"
            session_key = current_session_id

        if session_key not in sessions:
            sessions[session_key] = []

        sessions[session_key].append(row)
        
        if row_time:
            last_time = row_time

    for session_key, session_rows in sessions.items():
        safe_filename = re.sub(r'[\\/*?:"<>|\n\r\t]', '', session_key).strip()
        if not safe_filename: safe_filename = "Unknown_Session"
        safe_filename = safe_filename[:60] 

        md_filename = f"{safe_filename}.md"
        final_md_path = output_path / md_filename
        
        body_content = ""
        processed_messages = 0

        for row in session_rows:
            date_str = row['date']
            author_str = row['author']
            message_str = row['message'].strip()
            
            if not message_str: continue
                
            body_content += f"### 🗣️ {author_str.capitalize()} "
            if date_str:
                parsed_d = safe_parse_date(date_str)
                display_date = parsed_d.strftime('%Y-%m-%d %H:%M') if parsed_d else date_str
                body_content += f"*( {display_date} )*"
            body_content += "\n\n"
            
            if author_str.lower() in ['user', 'human', 'client']:
                formatted_message = "\n".join([f"> {line}" for line in message_str.split('\n')])
                body_content += f"{formatted_message}\n\n"
            else:
                body_content += f"{message_str}\n\n"
                
            body_content += "---\n\n"
            processed_messages += 1

        if processed_messages == 0:
            continue

        session_hash = get_content_hash(body_content)

        if session_registry.get(session_key) == session_hash:
            print(f"  [SKIP] '{safe_filename}' (Session already exported)")
            continue

        # Ensure Inbox exists before writing the first new/updated file
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)

        with open(final_md_path, mode='w', encoding='utf-8') as md_file:
            md_file.write(f"# {session_key}\n")
            md_file.write(f"> **Imported at:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            md_file.write(f"> **Source file:** {input_path.name}\n\n")
            md_file.write("---\n\n")
            md_file.write(body_content)

        session_registry[session_key] = session_hash
        print(f"  [OK] Exported '{safe_filename}.md' -> {processed_messages} messages.")

# ==========================================
# MAIN IMPORT PROCESS
# ==========================================

def run_import(vault_base_path=None):
    """
    Scans 'import/' folder for both CSV and JSON, creating a temporary Inbox.
    Uses a two-level registry to avoid processing duplicate files and sessions.
    Deletes the original files from the import folder after processing.
    """
    if not vault_base_path:
        vault_base_path = Path.home() / "Documents" / "Re.mind vault"
    else:
        vault_base_path = Path(vault_base_path)

    import_folder = vault_base_path / "import"
    
    remind_folder = vault_base_path / ".remind"
    remind_folder.mkdir(parents=True, exist_ok=True)
    registry_path = remind_folder / ".registry.json"
    
    if not import_folder.exists():
        print(f"[*] Creating global import folder at: {import_folder}")
        import_folder.mkdir(parents=True, exist_ok=True)
        print("[!] The import folder was empty. Please place your .csv or .json files there.")
        return

    import_files = list(import_folder.glob("*.csv")) + list(import_folder.glob("*.json"))
    
    if not import_files:
        print(f"[-] No .csv or .json files found in '{import_folder}'.")
        return

    # Load registry and separate file hashes from session hashes
    registry = load_registry(registry_path)
    files_registry = registry.get("files", {})
    sessions_registry = registry.get("sessions", {})
    
    files_to_process = []

    for file_path in import_files:
        file_hash = get_file_hash(file_path)
        # Check if file is new or modified
        if file_path.name not in files_registry or files_registry[file_path.name] != file_hash:
            files_to_process.append((file_path, file_hash))
        else:
            print(f"  [SKIP] '{file_path.name}' (File unchanged).")
            # Delete skipped files as well to keep the folder clean
            try:
                file_path.unlink()
                print(f"  [OK] Deleted '{file_path.name}' (Already imported).")
            except Exception as e:
                print(f"  [!] Could not delete '{file_path.name}': {e}")

    if not files_to_process:
        print("\n[+] No new files to import. Everything is up to date.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    inbox_folder = vault_base_path / f"_Inbox_{timestamp}"
    
    print(f"[*] Starting batch import ({len(files_to_process)} new/modified files found)...")
    
    for file_path, file_hash in files_to_process:
        process_file_to_markdown(file_path, inbox_folder, sessions_registry)
        # Register file as successfully processed
        files_registry[file_path.name] = file_hash
        # Delete the file after processing
        try:
            file_path.unlink()
            print(f"  [OK] Deleted '{file_path.name}' from import folder.")
        except Exception as e:
            print(f"  [!] Could not delete '{file_path.name}': {e}")
        
    # Save the updated registry
    registry["files"] = files_registry
    registry["sessions"] = sessions_registry
    save_registry(registry_path, registry)
        
    if inbox_folder.exists():
        print(f"\n[+] Import finished successfully. Check '{inbox_folder.name}'.")
    else:
        print("\n[+] Import finished. No new sessions were extracted (all were duplicates).")

if __name__ == "__main__":
    pass