import os
import shutil
import sys
import traceback
from pathlib import Path

# Adjust path to import from the core module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.importer import run_import

def setup_test_environment(source_files):
    """
    Creates an isolated test vault and copies all specified real files into it.
    """
    base_path = Path("test_vault")
    import_path = base_path / "import"
    
    # Clean previous test runs if they exist
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
        else:
            print(f"[!] Warning: Source file '{source_path.name}' not found.")

    if copied_count == 0:
        raise FileNotFoundError(
            "None of the specified source files were found.\n"
            "[DEBUG] Please ensure your CSV/JSON files are in the same folder as this script."
        )

    return base_path

if __name__ == "__main__":
    # Test Copilot CSV, Gemini JSON, and ChatGPT JSON files at the same time
    base_dir = Path(__file__).parent.parent
    test_files = [
        "copilot-activity-history.csv",
        "MiActividad.json",
        "chatgpt export/conversations-000.json",
        "chatgpt export/conversations-001.json"
    ]
    
    actual_test_files = []
    for f in test_files:
        if (base_dir / f).exists():
            actual_test_files.append(str(base_dir / f))
        elif Path(f).exists():
            actual_test_files.append(f)
            
    if not actual_test_files:
        print("[!] No test files found. Cannot run test.")
        sys.exit(1)
        
    try:
        print("[*] Setting up isolated test environment...")
        test_vault = setup_test_environment(actual_test_files)

        print("[*] Running core.importer...")
        print("-" * 50)
        
        # Run the importer pointing to our test vault
        run_import(vault_base_path=test_vault)
        
        print("-" * 50)
        print("[*] Checking generated files...")
        
        # Locate the dynamically generated Inbox folder
        inbox_dirs = list(test_vault.glob("_Inbox_*"))
        
        if inbox_dirs:
            inbox = inbox_dirs[0]
            generated_mds = list(inbox.glob("*.md"))
            
            if generated_mds:
                print(f"[OK] Success! {len(generated_mds)} Markdown files generated.")
                for md_file in generated_mds:
                    print(f"  -> {md_file.name} ({md_file.stat().st_size / 1024:.2f} KB)")
                print("\n[*] You can now open these files in your Markdown editor to verify the formatting.")
            else:
                print(f"[!] Error: No Markdown files were generated in the Inbox.")
                print(f"[DEBUG] Contents of Inbox: {[f.name for f in inbox.iterdir()]}")
        else:
            print("[!] Error: Inbox folder was not created.")
            print(f"[DEBUG] Contents of test_vault: {[f.name for f in test_vault.iterdir()]}")
            
    except Exception as e:
        print("\n[CRITICAL FAILURE] An error occurred during the test process:")
        print(f"[DEBUG] Exception Type: {type(e).__name__}")
        print(f"[DEBUG] Error Message: {str(e)}")
        print("[DEBUG] Full Traceback:")
        print("-" * 50)
        traceback.print_exc()
        print("-" * 50)