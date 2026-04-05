import argparse
import re
import sys
import platform
import json
from pathlib import Path

# Import core modules
from .core.importer import run_import
from .core.indexer import index_notebook
from .core.resolver import list_project_tags, find_nodes_by_tag, display_global_state, display_navigation_tree
from .core.extractor import run_extractor
from .core.writer import execute_write

CONFIG_FILE = Path.home() / ".remindrc"

# ==========================================
# VAULT CONFIGURATION
# ==========================================

def get_vault_path():
    """Returns the absolute path to the Re.mind vault, checking config first, then OS directly."""
    # 1. Check custom config first
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if "vault_path" in config:
                    return Path(config["vault_path"])
        except Exception as e:
            print(f"[-] Error reading config file: {e}")

    # 2. Default fallback
    docs_path = Path.home() / "Documents"
    try:
        system = platform.system()
        if system == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            path_str, _ = winreg.QueryValueEx(key, "Personal")
            docs_path = Path(path_str)
        elif system == "Linux":
            config_file = Path.home() / ".config" / "user-dirs.dirs"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.startswith("XDG_DOCUMENTS_DIR"):
                            path_str = line.split('=')[1].strip().strip('"')
                            path_str = path_str.replace("$HOME", str(Path.home()))
                            docs_path = Path(path_str)
                            break
    except Exception:
        pass

    return docs_path / "Re.mind vault"

def expand_braces(argument):
    """
    Unpacks brace syntax (e.g. test.{a,b}) for cross-platform support.
    """
    match = re.search(r"(.*?)\.\{(.*?)\}", argument)
    if match:
        prefix = match.group(1)
        content = match.group(2)
        elements = content.split(',')
        return [f"{prefix}.{element.strip()}" for element in elements]
    return [argument]

# ==========================================
# COMMAND HANDLERS
# ==========================================

def handle_install(args):
    vault_path = get_vault_path()
    print(f"[*] Ensuring vault directory exists at: {vault_path}")
    vault_path.mkdir(parents=True, exist_ok=True)
    
    agent_dir = Path.home() / ".agents" / "skills" / "remind"
    print(f"[*] Deploying SKILL.md to: {agent_dir}")
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    skill_file = agent_dir / "SKILL.md"
    
    import importlib.resources
    try:
        skill_data = importlib.resources.files("remind").joinpath("SKILL.md").read_bytes()
        if skill_file.exists():
            skill_file.unlink()
        skill_file.write_bytes(skill_data)
        print(f"[+] Successfully copied SKILL.md to {skill_file}")
    except Exception as e:
        print(f"[-] Error reading SKILL.md from PyPI package: {e}")
        sys.exit(1)
        
    print("[+] Install complete.")

def handle_init(args):
    vault_path = get_vault_path()
    project_dir_name = args.name.replace(" ", "_")
    project_path = vault_path / project_dir_name
    
    if project_path.exists():
        print(f"[-] Error: Project '{project_dir_name}' already exists in the vault.")
        sys.exit(1)
        
    print(f"[*] Initializing new Re.mind project: '{args.name}'")
    print(f"[*] Creating directory at: {project_path}")
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Generate the base map.index using our indexer
    index_notebook(project_path)
    print(f"\n[+] Project '{args.name}' initialized successfully.")
    
def handle_config(args):
    """Saves a custom vault path to the configuration file."""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            pass # Si el archivo está corrupto, lo sobreescribimos

    # Usamos resolve() para asegurar que guardamos la ruta absoluta
    # incluso si el usuario introduce una ruta relativa como "./mi_vault"
    custom_path = Path(args.path).resolve()
    config["vault_path"] = str(custom_path)

    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"[+] Vault location updated to: {custom_path}")
        
        # Opcional: Crear la carpeta si no existe
        if not custom_path.exists():
            custom_path.mkdir(parents=True, exist_ok=True)
            print(f"[+] Created new vault directory.")
    except Exception as e:
        print(f"[-] Error saving config: {e}")
        sys.exit(1)
        
def handle_import(args):
    vault_path = get_vault_path()
    # Calls the importer module to process CSV/JSON into _Inbox folders
    run_import(vault_base_path=vault_path)

def handle_index(args):
    vault_path = get_vault_path()
    target_project = args.project
    
    if target_project:
        project_path = vault_path / target_project
        if not project_path.exists():
            print(f"[-] Error: Project '{target_project}' not found in {vault_path}")
            sys.exit(1)
        print(f"[*] Indexing specific project: {target_project}...")
        index_notebook(project_path)
    else:
        print("[*] Indexing all projects in the vault...")
        # Scan the vault for all valid project folders
        for item in vault_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'import':
                print(f"\n[*] Processing notebook: {item.name}")
                index_notebook(item)
                
    print("\n[+] Indexing process complete.")

def handle_map(args):
    vault_path = get_vault_path()
    if args.path:
        display_navigation_tree(vault_path, args.path)
    else:
        display_global_state(vault_path)

def handle_tag(args):
    vault_path = get_vault_path()
    project = args.project_hash
    tag = args.tag
    
    # If the user asks for a list, display all tags
    if tag.lower() == "list":
        list_project_tags(vault_path, project)
    else:
        # Otherwise, search for the specific tag
        print(f"[*] Searching for tag '#{tag}' in project '{project}'...")
        paths = find_nodes_by_tag(vault_path, project, tag)
        
        # Output a helpful hint to extract all found documents at once
        if paths:
            paths_str = " ".join(paths)
            print(f"\n[*] Tip: Extract them all instantly by running:")
            print(f"    remind me {paths_str}")

def handle_me(args):
    vault_path = get_vault_path()
    raw_paths = args.paths
    expanded_paths = []
    
    for path in raw_paths:
        expanded_paths.extend(expand_braces(path))
        
    print(f"[*] Extracting content from {len(expanded_paths)} nodes...")
    for path in expanded_paths:
        print(f"  -> Resolving and extracting: {path}")
    
    run_extractor(vault_path, expanded_paths)

def handle_write(args):
    vault_path = get_vault_path()
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[-] Error reading temporary file: {e}")
        sys.exit(1)
        
    execute_write(vault_path, args.path, content, mode='w')

def handle_append(args):
    vault_path = get_vault_path()
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[-] Error reading temporary file: {e}")
        sys.exit(1)
        
    execute_write(vault_path, args.path, content, mode='a')

# ==========================================
# ARGUMENT PARSER CONFIGURATION
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        prog="remind",
        description="Re.mind - CLI for semantic knowledge management and extraction.",
        epilog="Run 'remind <command> --help' for more information on a specific command."
    )
    
    subparsers = parser.add_subparsers(title="Available commands", dest="command")
    subparsers.required = True

    # 0. INSTALL
    parser_install = subparsers.add_parser("install", help="Creates the vault directory and deploys SKILL.md to the global agent directory.")
    parser_install.set_defaults(func=handle_install)

    # 1. INIT
    parser_init = subparsers.add_parser("init", help="Initializes a new Re.mind notebook in the Vault.")
    parser_init.add_argument("name", type=str, help="Project name (e.g. 'My Project').")
    parser_init.set_defaults(func=handle_init)

    # 2. IMPORT
    parser_import = subparsers.add_parser("import", help="Imports raw exports and generates Markdown notebooks.")
    parser_import.set_defaults(func=handle_import)

    # 3. INDEX
    parser_index = subparsers.add_parser("index", help="Compiles Markdown files, updates sidecars and map.index.")
    parser_index.add_argument("project", nargs="?", type=str, help="Specific project to index (optional).")
    parser_index.set_defaults(func=handle_index)

    # 4. MAP
    parser_map = subparsers.add_parser("map", help="Queries the index structure without extracting content.")
    parser_map.add_argument("path", nargs="?", type=str, help="Partial logical path to explore (optional).")
    parser_map.set_defaults(func=handle_map)

    # 5. TAG
    parser_tag = subparsers.add_parser("tag", help="Performs a transversal search for a specific tag.")
    parser_tag.add_argument("project_hash", type=str, help="Unique hash of the project.")
    parser_tag.add_argument("tag", type=str, help="Tag name to search for (without #).")
    parser_tag.set_defaults(func=handle_tag)

    # 6. ME
    parser_me = subparsers.add_parser("me", help="Extracts the exact content of one or more nodes.")
    parser_me.add_argument("paths", nargs="+", type=str, help="Logical paths to extract. Supports {a,b} syntax.")
    parser_me.set_defaults(func=handle_me)

    # 7. WRITE
    parser_write = subparsers.add_parser("write", help="Writes content to a specific file in the vault from a temporary file.")
    parser_write.add_argument("path", type=str, help="Logical path in the vault.")
    parser_write.add_argument("--file", type=str, required=True, help="Path to the temporary file containing the content to write.")
    parser_write.set_defaults(func=handle_write)

    # 8. APPEND
    parser_append = subparsers.add_parser("append", help="Appends content to a specific file in the vault from a temporary file.")
    parser_append.add_argument("path", type=str, help="Logical path in the vault.")
    parser_append.add_argument("--file", type=str, required=True, help="Path to the temporary file containing the content to append.")
    parser_append.set_defaults(func=handle_append)

    # 9. CONFIG
    parser_config = subparsers.add_parser("config", help="Configures global CLI settings.")
    parser_config.add_argument("--set-vault", dest="path", type=str, required=True, help="Sets a custom absolute or relative path for the vault.")
    parser_config.set_defaults(func=handle_config)

    args = parser.parse_args()
    
    try:
        args.func(args)
    except Exception as e:
        import traceback
        print(f"\n[CRITICAL FAILURE] Execution error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()