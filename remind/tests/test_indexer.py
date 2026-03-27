import os
import shutil
import sys
import json
import traceback
from pathlib import Path

# Adjust path to import from the core module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.importer import run_import
from core.indexer import index_notebook

def setup_test_environment(source_files):
    """
    Creates an isolated test vault and copies real files into it.
    """
    base_path = Path("test_vault")
    import_path = base_path / "import"
    
    if base_path.exists():
        shutil.rmtree(base_path)
        
    import_path.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    for source_name in source_files:
        source_path = Path(source_name)
        if source_path.exists():
            destination_path = import_path / source_path.name
            shutil.copy2(source_path, destination_path)
            print(f"[*] Copied '{source_path.name}' to test import folder.")
            copied_count += 1

    if copied_count == 0:
        raise FileNotFoundError(
            "None of the specified source files were found.\n"
            "[DEBUG] Please ensure your CSV/JSON files are in the same folder as this script."
        )

    return base_path

if __name__ == "__main__":
    test_files = [
        "copilot-activity-history.csv",
        "MiActividad.json"
    ]
    
    try:
        print("\n[*] Setting up isolated test environment...")
        test_vault = setup_test_environment(test_files)

        print("\n" + "="*50)
        print("[1] RUNNING IMPORTER")
        print("="*50)
        run_import(vault_base_path=test_vault)
        
        # Locate the dynamically generated Inbox folder
        inbox_dirs = list(test_vault.glob("_Inbox_*"))
        if not inbox_dirs:
            raise RuntimeError("Inbox folder was not created by the importer.")
            
        inbox = inbox_dirs[0]
        
        print("\n" + "="*50)
        print("[2] RUNNING INDEXER ON INBOX")
        print("="*50)
        # We index the Inbox just like any standard notebook project
        index_notebook(inbox)
        
        print("\n" + "="*50)
        print("[3] VERIFYING ARTIFACTS")
        print("="*50)
        
        # Verify map.index existence and content
        map_index_path = inbox / "map.index"
        if map_index_path.exists():
            print(f"[OK] map.index generated successfully ({map_index_path.stat().st_size / 1024:.2f} KB).")
            with open(map_index_path, "r", encoding="utf-8") as f:
                map_data = json.load(f)
                project_slug = list(map_data.keys())[0]
                print(f"  -> Project Slug generated: {project_slug}")
                print(f"  -> Indexed at: {map_data[project_slug]['_meta']['indexed_at']}")
        else:
            print("[!] Error: map.index not found!")
            
        # Verify sidecars
        md_files = list(inbox.glob("*.md"))
        sidecars = list(inbox.glob("*.sidecar.json"))
        
        print(f"\n[*] Found {len(md_files)} Markdown files and {len(sidecars)} Sidecar files.")
        
        if len(md_files) > 0 and len(md_files) == len(sidecars):
            print("[OK] Match: All Markdown files have their corresponding sidecar.")
            
            # Inspect the first sidecar generated
            with open(sidecars[0], "r", encoding="utf-8") as f:
                sc_data = json.load(f)
                print(f"\n[*] Inspecting sidecar: {sidecars[0].name}")
                print(f"  -> Schema used: {sc_data.get('schema')}")
                print(f"  -> Logical Key (Identity): {sc_data.get('identity', {}).get('logical_key')}")
                print(f"  -> Target File: {sc_data.get('file', {}).get('relative_path')}")
                print(f"  -> Epigraphes (Blocks) detected: {len(sc_data.get('blocks', {}))}")
        else:
            print("[!] Warning: Mismatch between number of Markdown files and Sidecars.")

        print("\n[+] Indexer test completed successfully.")

    except Exception as e:
        print("\n[CRITICAL FAILURE] An error occurred during the test process:")
        print(f"[DEBUG] Exception Type: {type(e).__name__}")
        print(f"[DEBUG] Error Message: {str(e)}")
        traceback.print_exc()