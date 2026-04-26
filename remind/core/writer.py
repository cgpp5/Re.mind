import sys
from pathlib import Path
from .resolver import load_project_map
from .indexer import index_notebook, generate_slug

def resolve_write_path(vault_path, logical_path, file_name=None):
    """
    Translates a logical path to a physical path.
    If file_name is provided, logical_path is treated as a project/directory path.
    Otherwise, logical_path is treated as the full logical file path.
    """
    parts = [part for part in logical_path.split('.') if part]
    if not parts or (file_name is None and len(parts) < 2):
        print(f"[-] Error: Invalid logical path '{logical_path}'.")
        sys.exit(1)

    if file_name is not None and not file_name.strip():
        print("[-] Error: Missing target file name.")
        sys.exit(1)

    if file_name is not None:
        file_name = file_name.strip()
        if Path(file_name).name != file_name:
            print(f"[-] Error: File name must be a single file name, got '{file_name}'.")
            sys.exit(1)

    project_slug = parts[0]
    project_dir, map_data = load_project_map(vault_path, project_slug)

    if not project_dir:
        print(f"[-] Error: Project with slug '{project_slug}' not found in vault.")
        sys.exit(1)

    current_node = map_data
    current_physical_path = project_dir

    for i, part in enumerate(parts[1:]):
        is_last = i == len(parts[1:]) - 1

        if current_node is not None and part in current_node:
            node_data = current_node[part]
            if "_dir" in node_data:
                current_physical_path = current_physical_path / node_data["_dir"]
                current_node = node_data
            elif "_file" in node_data:
                if file_name is not None:
                    print(f"[-] Error: '{part}' is a file. Provide only a project/directory path and pass the actual file name separately.")
                    sys.exit(1)
                current_physical_path = current_physical_path / node_data["_file"]
                if not is_last:
                    print(f"[-] Error: '{part}' is a file, cannot contain children.")
                    sys.exit(1)
                current_node = None
            elif "_title" in node_data:
                target_hint = "project/directory path" if file_name is not None else "path to a file"
                print(f"[-] Error: Cannot write directly to a heading block '{part}'. Provide a {target_hint}.")
                sys.exit(1)
            else:
                # E.g. _meta, _tags
                print(f"[-] Error: Invalid path part '{part}'.")
                sys.exit(1)
        else:
            if file_name is None and is_last:
                current_physical_path = current_physical_path / f"{part}.md"
            else:
                current_physical_path = current_physical_path / part
            current_node = None

    if file_name is not None:
        current_physical_path = current_physical_path / f"{file_name}.md"

    return project_dir, current_physical_path

def execute_write(vault_path, logical_path, content, mode="w", file_name=None):
    """
    Creates or overwrites/appends a file, then re-indexes the project.
    """
    project_dir, target_file = resolve_write_path(vault_path, logical_path, file_name)

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
        if file_name is not None:
            parts = [p for p in logical_path.split('.') if p]
            file_slug = generate_slug(file_name, level=2, context="".join(parts))
            print(f"[+] Document slug (logical key): {logical_path}.{file_slug}")
    except Exception as e:
        print(f"[-] Error writing to {target_file}: {e}")
        sys.exit(1)
    
    # Silently run indexer on the project
    try:
        index_notebook(project_dir)
        print(f"[*] Auto-indexed project '{project_dir.name}'.")
    except Exception as e:
        print(f"[-] Warning: Auto-indexing failed: {e}")
