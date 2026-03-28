import sys
from pathlib import Path
from .resolver import load_project_map
from .indexer import index_notebook

def resolve_write_path(vault_path, logical_path):
    """
    Translates a logical path to a physical path, inventing directories
    and files if they don't exist in map.index.
    """
    parts = logical_path.split('.')
    if len(parts) < 2:
        print(f"[-] Error: Invalid logical path '{logical_path}'. Needs at least 'project.file'")
        sys.exit(1)

    project_hash = parts[0]
    project_dir, map_data = load_project_map(vault_path, project_hash)

    if not project_dir:
        print(f"[-] Error: Project with hash '{project_hash}' not found in vault.")
        sys.exit(1)

    current_node = map_data
    current_physical_path = project_dir

    for i, part in enumerate(parts[1:]):
        is_last = (i == len(parts[1:]) - 1)

        if current_node is not None and part in current_node:
            node_data = current_node[part]
            if "_dir" in node_data:
                current_physical_path = current_physical_path / node_data["_dir"]
                current_node = node_data
            elif "_file" in node_data:
                current_physical_path = current_physical_path / node_data["_file"]
                if not is_last:
                    print(f"[-] Error: '{part}' is a file, cannot contain children.")
                    sys.exit(1)
                current_node = None
            elif "_title" in node_data:
                print(f"[-] Error: Cannot write directly to a heading block '{part}'. Provide a path to a file.")
                sys.exit(1)
            else:
                # E.g. _meta, _tags
                print(f"[-] Error: Invalid path part '{part}'.")
                sys.exit(1)
        else:
            # We are inventing a new path or traversing newly invented ones
            if is_last:
                current_physical_path = current_physical_path / f"{part}.md"
            else:
                current_physical_path = current_physical_path / part
            
            # Since this node didn't exist, all subsequent nodes won't exist in map_data either
            current_node = None

    return project_dir, current_physical_path

def execute_write(vault_path, logical_path, content, mode="w"):
    """
    Creates or overwrites/appends a file, then re-indexes the project.
    """
    project_dir, target_file = resolve_write_path(vault_path, logical_path)

    # Ensure parent directories exist
    target_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if mode == 'a' and target_file.exists() and target_file.stat().st_size > 0:
            # If the file exists and is not empty, ensure we append on a new line
            with open(target_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                last_char = file_content[-1] if file_content else '\n'
            
            with open(target_file, 'a', encoding='utf-8') as f:
                if last_char != '\n':
                    f.write("\n")
                f.write(content)
        else:
            with open(target_file, mode, encoding='utf-8') as f:
                f.write(content)
                
        print(f"[+] Successfully wrote to {target_file.relative_to(project_dir)}")
    except Exception as e:
        print(f"[-] Error writing to {target_file}: {e}")
        sys.exit(1)
    
    # Silently run indexer on the project
    try:
        index_notebook(project_dir)
        print(f"[*] Auto-indexed project '{project_dir.name}'.")
    except Exception as e:
        print(f"[-] Warning: Auto-indexing failed: {e}")
