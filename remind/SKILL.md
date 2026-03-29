---
name: remind-cli
description: This skill allows you to access and interact with the Re.mind Vault. The Re.mind Vault is an offline curated Markdown-based knowledge repository that helps users organize their thoughts and ideas, remind-cli gives AI agents the tools to navigate it efficiently.
---

### Core Commands & Workflow

1. **Initialization & Ingestion**
   * `remind init [project_name]`: Initializes a new project in the Vault, creating the base `map.index` JSON and unique project hash.
   * `remind import`: Scans the global `import/` folder, processes raw exports (CSV/JSON), and generates temporary `_Inbox_` Markdown files grouped by session.

2. **Indexing**
   * `remind index [project_hash]`: Scans the folder structure, compiles `.md` files, extracts inline tags (e.g., `#testing`), updates exact line numbers in JSON sidecars, and rebuilds `map.index`. 
   * *Rule:* Must be executed whenever Markdown files are manually edited or reorganized.

3. **Writing & Modifying (AI-Optimized)**
   * `remind write <logical_path> --file <path>`: Creates a new node or overwrites an existing one using content from a temporary file. 
   * `remind append <logical_path> --file <path>`: Appends content from a temporary file to the end of an existing node.
   * *Critical Rule:* Always write your intended Markdown content to a temporary file first, then execute these commands using the `--file` flag. This prevents shell escaping issues with newlines and special characters.

   **Example Workflow (PowerShell):**
   1. `$tmp = New-TemporaryFile`
   2. `Set-Content -Path $tmp.FullName -Value "Your multi-line content" -Encoding UTF8`
   3. `remind write project.folder.file --file $tmp.FullName`
   4. `Remove-Item $tmp.FullName`

4. **Querying & Navigation (Read-Only)**
   * `remind map [logical_path]`: Universal command to query the knowledge structure. Used without arguments, it returns the global Vault state.
   * `remind tag <project_hash> list`: Returns a table of all existing tags sorted by popularity.
   * `remind tag <project_hash> <tag>`: Performs a cross-sectional search ignoring folders, returning logical paths that contain the specified tag.
   * `remind me <paths>`: Command that fetches text content from the vault. Resolves hierarchy via JSON and outputs the exact content of nodes. You must provide a full path to the node without skipping any levels. Supports brace expansion (e.g., `remind me testprojea1b.fe.spec.{fsadx1a,fsbol2b}`).

### Common Issues & Best Practices
* **Missing content:** If recent changes cannot be found, run `remind index` to update the index.
* **Brace Expansion:** The CLI handles `{}` internally using regex in Python, ensuring cross-platform support regardless of terminal (Bash/Zsh vs CMD/PowerShell). 