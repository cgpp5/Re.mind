import json
import sys
from pathlib import Path

def find_project_in_vault(vault_path, project_hash):
    """
    Scans the vault to find which project directory contains the given project_hash.
    """
    for item in vault_path.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name != 'import':
            map_file = item / ".remind" / "map.index"
            if map_file.exists():
                try:
                    with open(map_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if project_hash in data:
                            return item, data[project_hash]
                except json.JSONDecodeError:
                    continue
    return None, None

def extract_node(vault_path, logical_path):
    """
    Resolves a logical path, reads the sidecar, and extracts the exact text block.
    """
    parts = logical_path.split('.')
    if len(parts) < 2:
        print(f"[-] Error: Invalid logical path '{logical_path}'. Needs at least 'project.file'")
        return

    project_hash = parts[0]
    project_dir, map_data = find_project_in_vault(vault_path, project_hash)

    if not project_dir:
        print(f"[-] Error: Project with hash '{project_hash}' not found in vault.")
        return

    # Traverse map.index to resolve the physical path
    current_node = map_data
    current_physical_path = project_dir
    target_file = None
    target_block_slug = None

    for i, part in enumerate(parts[1:]):
        if part not in current_node:
            print(f"[-] Error: Node '{part}' not found in logical path '{logical_path}'.")
            return
        
        current_node = current_node[part]

        if "_dir" in current_node:
            current_physical_path = current_physical_path / current_node["_dir"]
        elif "_file" in current_node:
            target_file = current_node["_file"]
            
            # We also need the logical file path to locate the sidecar in .remind/sidecars
            # The logical file path is the parts up to and including the file slug
            logical_file_path = ".".join(parts[:i+2])
            
            # If there's another part after the file, it must be the heading/block slug
            remaining_parts = parts[1:][i+1:]
            if remaining_parts:
                target_block_slug = remaining_parts[0]
                # Check if the block actually exists in the map.index under this file
                if target_block_slug not in current_node:
                     print(f"[-] Error: Block '{target_block_slug}' not found in file '{target_file}'.")
                     return
            break

    if not target_file:
        print(f"[-] Error: Path '{logical_path}' points to a directory, not a file or block.")
        print(f"[*] Hint: Use 'remind map {logical_path}' to explore its contents.")
        return

    # Build physical paths
    md_path = current_physical_path / target_file
    sidecar_path = project_dir / ".remind" / "sidecars" / f"{logical_file_path}.sidecar.json"

    if not md_path.exists():
        print(f"[-] Error: Physical file not found at {md_path}")
        return
        
    if not sidecar_path.exists():
        print(f"[-] Error: Sidecar not found at {sidecar_path}")
        return

    # Read sidecar to get line ranges
    try:
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            sidecar = json.load(f)
    except json.JSONDecodeError:
        print(f"[-] Error: Invalid JSON in sidecar '{sidecar_path.name}'")
        return

    start_line = 1
    end_line = None

    if target_block_slug:
        blocks = sidecar.get("blocks", {})
        if target_block_slug not in blocks:
             print(f"[-] Error: Block '{target_block_slug}' not found in sidecar.")
             return
        
        range_data = blocks[target_block_slug].get("range", {})
        start_line = range_data.get("start_line", 1)
        end_line = range_data.get("end_line")

    # Extract text from Markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if end_line is None:
        end_line = len(lines)

    # start_line and end_line are 1-indexed. Slicing in Python is 0-indexed.
    extracted_lines = lines[start_line - 1 : end_line]
    extracted_text = "".join(extracted_lines)

    # Print output cleanly for the AI / User
    print(f"\n📄 SOURCE: {logical_path} ({md_path.relative_to(project_dir)})")
    print("=" * 70)
    print(extracted_text.strip('\n'))
    print("=" * 70)

def run_extractor(vault_path, logical_paths):
    """
    Processes multiple logical paths and extracts their content to the terminal.
    """
    for path in logical_paths:
        extract_node(vault_path, path)