import os
import re
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

# ==========================================
# SLUG GENERATION
# ==========================================

def clean_text(text):
    """Removes special characters and leaves only lowercase alphanumeric chars."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def generate_slug(text, level, context=""):
    """
    Generates a deterministic slug based on the hierarchical level.
    Root (12), Directory (2), File (4), Node/Heading (7)
    If the normalized name is shorter than the target length, it is used as-is.
    """
    cleaned_text = clean_text(text)

    if level == 0:
        if len(cleaned_text) < 12:
            return cleaned_text
        base = cleaned_text[:9].ljust(9, 'a')
        m_hash = hashlib.md5((context + text).encode('utf-8')).hexdigest()
        return f"{base}{m_hash[:3]}"
    elif level == 1:
        if len(cleaned_text) < 2:
            return cleaned_text
        return cleaned_text[:2].ljust(2, 'a')
    elif level == 2:
        if len(cleaned_text) < 4:
            return cleaned_text
        return cleaned_text[:4].ljust(4, 'a')
    else:
        if len(cleaned_text) < 7:
            return cleaned_text
        base = cleaned_text[:5].ljust(5, 'a')
        m_hash = hashlib.md5((context + text).encode('utf-8')).hexdigest()
        return f"{base}{m_hash[:2]}"

# ==========================================
# MARKDOWN & METADATA PARSER
# ==========================================

# Regex to find inline tags like #urgent or #api-design
# (?<!\S) ensures it's preceded by whitespace or start of line (avoids URLs or Hex colors)
# ([\w\-]+) matches word characters (including accents/ñ) and hyphens
TAG_REGEX = r'(?<!\S)#([\w\-]+)'

def analyze_md_file(file_path):
    """
    Reads a Markdown file, calculates technical metadata (hash, encoding, line endings),
    detects content blocks (headings) with their exact lines, and extracts inline #tags
    at the document level.
    """
    with open(file_path, 'rb') as f:
        raw_content = f.read()
        
    content_hash = f"sha256:{hashlib.sha256(raw_content).hexdigest()}"
    line_endings = "crlf" if b'\r\n' in raw_content else "lf"
    
    text = raw_content.decode('utf-8', errors='replace')
    lines = text.splitlines() 
    
    detected_blocks = []
    current_block = None
    file_tags = set()
    
    for line_num, content in enumerate(lines, start=1):
        # 1. Check if the line is a Markdown Heading
        match = re.match(r'^(#+)\s+(.*)', content)
        
        if match:
            # Close previous block
            if current_block:
                current_block['end_line'] = line_num - 1
                detected_blocks.append(current_block)
                
            header_level = len(match.group(1))
            title = match.group(2).strip()
            
            # Open new block
            current_block = {
                'title': title,
                'level': header_level,
                'start_line': line_num,
                'end_line': len(lines)
            }
        elif not current_block and content.strip():
            # Handle text that appears before any heading in the document
            current_block = {
                'title': 'Document Root',
                'level': 0,
                'start_line': 1,
                'end_line': len(lines)
            }

        # 2. Extract inline tags from the current line (Document level only)
        line_tags = set(re.findall(TAG_REGEX, content))
        if line_tags:
            # Lowercase all tags to ensure case-insensitive matching (#Python == #python)
            normalized_tags = {t.lower() for t in line_tags}
            file_tags.update(normalized_tags)
            
    # Close the final block
    if current_block:
        detected_blocks.append(current_block)
        
    return {
        "hash": content_hash,
        "line_endings": line_endings,
        "encoding": "utf-8",
        "tags": list(file_tags),
        "blocks": detected_blocks
    }

# ==========================================
# MAIN INDEXING ENGINE
# ==========================================

def index_notebook(notebook_path):
    """
    Recursively scans a notebook.
    Generates the global map.index and one *.sidecar.json per document inside the .remind folder.
    """
    path = Path(notebook_path)
    
    if not path.exists() or not path.is_dir():
        print(f"[-] Error: Notebook does not exist at {path}")
        return

    project_name = path.name
    project_slug = generate_slug(project_name, level=0)
    
    # Initialize the .remind directory structure
    remind_dir = path / ".remind"
    sidecars_dir = remind_dir / "sidecars"
    
    remind_dir.mkdir(exist_ok=True)
    if sidecars_dir.exists():
        shutil.rmtree(sidecars_dir)
    sidecars_dir.mkdir(exist_ok=True)
    
    semantic_map = {
        project_slug: {
            "_meta": {
                "project_name": project_name,
                "indexed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "_tags": {} # The global inverse index for all tags
        }
    }
    
    generated_sidecars = 0
    global_tags_ref = semantic_map[project_slug]["_tags"]
    
    for root, dirs, files in os.walk(path):
        # Ignore hidden folders and the global 'import' folder if accidentally inside
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'import']
        
        current_path = Path(root)
        relative_parts = current_path.relative_to(path).parts
        
        current_node = semantic_map[project_slug]
        current_logical_path = [project_slug]
        
        # Build directory tree in JSON
        for i, part in enumerate(relative_parts):
            dir_slug = generate_slug(part, level=1 if i == 0 else 2, context="".join(current_logical_path))
            if dir_slug not in current_node:
                current_node[dir_slug] = {"_dir": part}
            current_node = current_node[dir_slug]
            current_logical_path.append(dir_slug)
            
        # Process files
        for file_name in files:
            # Ignore SKILL.md explicitly and non-markdown files
            if not file_name.endswith('.md') or file_name.lower() == 'skill.md':
                continue
                
            physical_file_path = current_path / file_name
            relative_vault_path = physical_file_path.relative_to(path)
            
            file_slug = generate_slug(file_name.replace('.md', ''), level=2, context="".join(current_logical_path))
            logical_file_path = ".".join(current_logical_path + [file_slug])
            
            # 1. Register file in Semantic Map
            current_node[file_slug] = {
                "_file": file_name
            }
            
            # 2. Analyze Markdown (Headings + Document Tags)
            analysis = analyze_md_file(physical_file_path)
            
            # 3. Prepare Sidecar structure (Schema v1)
            now_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            
            sidecar = {
                "schema": "doc-cli.sidecar.v1",
                "identity": {
                    "project_id": project_slug,
                    "logical_key": ".".join(current_logical_path[1:] + [file_slug]) if len(current_logical_path) > 1 else file_slug,
                    "source": "manual", 
                    "indexed_at": now_timestamp 
                },
                "file": {
                    "relative_path": str(relative_vault_path).replace("\\", "/"),
                    "encoding": analysis["encoding"],
                    "line_endings": analysis["line_endings"],
                    "tags": analysis["tags"] # Document-level tags
                },
                "blocks": {},
                "integrity": {
                    "content_hash": analysis["hash"],
                    "indexed_at": now_timestamp
                }
            }
            
            # 4. Fill blocks in Sidecar and map.index (No tag tracking per block)
            for block in analysis["blocks"]:
                heading_slug = generate_slug(block['title'], level=3, context=logical_file_path)
                
                # To Semantic Map
                current_node[file_slug][heading_slug] = {
                    "_title": block['title']
                }
                
                # To Sidecar (Strict Schema)
                sidecar["blocks"][heading_slug] = {
                    "type": "heading",
                    "level": block['level'],
                    "title": block['title'],
                    "range": {
                        "start_line": block['start_line'],
                        "end_line": block['end_line']
                    }
                }
                
            # 5. Populate the global inverse tag index (_tags) at the DOCUMENT level
            for tag in analysis['tags']:
                if tag not in global_tags_ref:
                    global_tags_ref[tag] = []
                # Append the logical file path (e.g., project.folder.file)
                if logical_file_path not in global_tags_ref[tag]:
                    global_tags_ref[tag].append(logical_file_path)
                
            # 6. Save Sidecar in the centralized .remind/sidecars folder
            sidecar_name = f"{logical_file_path}.sidecar.json"
            sidecar_path = sidecars_dir / sidecar_name
            
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(sidecar, f, indent=2, ensure_ascii=False)
                
            generated_sidecars += 1

    # ==========================================
    # SAVE GLOBAL MAP
    # ==========================================
    map_path = remind_dir / "map.index"
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(semantic_map, f, indent=2, ensure_ascii=False)
        
    print(f"  [OK] Index updated for '{project_name}'.")
    print(f"  [OK] Documents indexed and sidecars generated: {generated_sidecars}")
    print(f"  [OK] Unique tags mapped globally: {len(global_tags_ref)}")

    return project_slug

if __name__ == "__main__":
    pass