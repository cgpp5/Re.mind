import json
from pathlib import Path

def load_project_map(vault_path, project_slug):
    """
    Scans the vault and returns the physical directory and map.index data
    for a specific project slug.
    """
    for item in vault_path.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name != 'import':
            map_file = item / ".remind" / "map.index"
            if map_file.exists():
                try:
                    with open(map_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if project_slug in data:
                            return item, data[project_slug]
                except json.JSONDecodeError:
                    continue
    return None, None

def list_project_tags(vault_path, project_slug):
    """
    Reads the global _tags index and prints all available tags 
    sorted by the number of documents that contain them.
    """
    _, map_data = load_project_map(vault_path, project_slug)
    
    if not map_data:
        print(f"[-] Error: Project with slug '{project_slug}' not found in vault.")
        return
    
    tags = map_data.get("_tags", {})
    if not tags:
        print(f"[*] No tags found in project '{project_slug}'.")
        print("[*] Hint: Write #tags in your Markdown files and run 'remind index'.")
        return
        
    print(f"\n🏷️  TAGS IN PROJECT '{project_slug}'")
    print("=" * 60)
    
    # Sort tags by frequency (descending) and then alphabetically
    sorted_tags = sorted(tags.items(), key=lambda item: (-len(item[1]), item[0]))
    
    for tag_name, logical_paths in sorted_tags:
        count = len(logical_paths)
        
        if count > 8:
            # If it has too many files, just show the count to avoid terminal flooding
            print(f"  #{tag_name.ljust(25)} ({count} files)")
        else:
            # For 8 or fewer files, list them one by one, aligning the columns cleanly
            first_line_prefix = f"  #{tag_name.ljust(25)} "
            empty_prefix = " " * len(first_line_prefix)
            
            for i, path in enumerate(logical_paths):
                if i == 0:
                    print(f"{first_line_prefix}({path})")
                else:
                    print(f"{empty_prefix}({path})")
        
    print("=" * 60)

def find_nodes_by_tag(vault_path, project_slug, tag_name):
    """
    Looks up a specific tag in the index and returns the list of logical paths.
    """
    _, map_data = load_project_map(vault_path, project_slug)
    
    if not map_data:
        print(f"[-] Error: Project with slug '{project_slug}' not found in vault.")
        return []
        
    tags = map_data.get("_tags", {})
    
    # Normalize the input (remove '#' if the user typed it)
    normalized_tag = tag_name.lower().replace('#', '')
    
    if normalized_tag not in tags:
        print(f"[-] No documents found with tag '#{normalized_tag}'.")
        return []
        
    paths = tags[normalized_tag]
    
    print(f"\n🔍 Found {len(paths)} document(s) with tag '#{normalized_tag}':")
    for p in paths:
        print(f"  -> {p}")
        
    return paths

def display_global_state(vault_path):
    """
    Displays the global state of all projects in the vault.
    Shows the project slug, node count, and number of available tags.
    """
    print("\n🌍 GLOBAL VAULT STATE")
    print("=" * 60)
    found = False
    for item in vault_path.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name != 'import':
            map_file = item / ".remind" / "map.index"
            if map_file.exists():
                try:
                    with open(map_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for proj_slug, proj_data in data.items():
                            meta = proj_data.get("_meta", {})
                            proj_name = meta.get("project_name", item.name)
                            tags = proj_data.get("_tags", {})
                            num_tags = len(tags)
                            
                            # Recursively count nodes (folders, files, headings)
                            def count_nodes(node):
                                c = 0
                                for k, v in node.items():
                                    if k not in ["_meta", "_tags", "_dir", "_file", "_title"]:
                                        if isinstance(v, dict):
                                            c += 1 + count_nodes(v)
                                return c
                            
                            num_nodes = count_nodes(proj_data)
                            
                            print(f"📦 {proj_name} [{proj_slug}]")
                            print(f"   Nodes: {num_nodes} | Tags: {num_tags}\n")
                            found = True
                except json.JSONDecodeError:
                    continue
    if not found:
        print("  No projects found in the vault.")
    print("=" * 60)

def display_navigation_tree(vault_path, logical_path):
    """
    Displays the visual tree for a specific logical path.
    """
    parts = logical_path.split('.')
    project_slug = parts[0]
    
    _, map_data = load_project_map(vault_path, project_slug)
    if not map_data:
        print(f"[-] Error: Project with slug '{project_slug}' not found in vault.")
        return
        
    # Traverse to the requested node
    current_node = map_data
    node_name = map_data.get("_meta", {}).get("project_name", project_slug)
    
    for i, part in enumerate(parts[1:]):
        if part in current_node:
            current_node = current_node[part]
            if "_dir" in current_node:
                node_name = current_node["_dir"]
            elif "_file" in current_node:
                node_name = current_node["_file"]
            elif "_title" in current_node:
                node_name = current_node["_title"]
            else:
                node_name = part
        else:
            print(f"[-] Error: Path '{logical_path}' not found. Stopped at '{part}'.")
            return
            
    # Check if the requested node is a directory, file or title
    is_dir = "_dir" in current_node or logical_path == project_hash
    suffix = "/" if is_dir else ""
            
    print(f"\n📦 [{logical_path}] {node_name}{suffix}")
    _print_tree(current_node, prefix="")

def _print_tree(node, prefix=""):
    # Filter out reserved keys
    children = [(k, v) for k, v in node.items() if k not in ["_meta", "_tags", "_dir", "_file", "_title"] and isinstance(v, dict)]
    
    # Helper to get the display name
    def get_name(k, v):
        if "_dir" in v: return v["_dir"] + "/"
        if "_file" in v: return v["_file"]
        if "_title" in v: return v["_title"]
        return k
        
    # Sort children alphabetically by their display name
    children.sort(key=lambda x: get_name(x[0], x[1]).lower())
    
    for i, (k, v) in enumerate(children):
        is_last = (i == len(children) - 1)
        connector = "└── " if is_last else "├── "
        
        name = get_name(k, v)
        print(f"{prefix}{connector}[{k}] {name}")
        
        new_prefix = prefix + ("    " if is_last else "│   ")
        _print_tree(v, new_prefix)