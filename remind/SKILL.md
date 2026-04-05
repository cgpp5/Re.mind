---
name: remind-cli
description: This skill allows you to access and interact with the Re.mind Vault. The Re.mind Vault is an offline curated Markdown-based knowledge repository that helps users organize their thoughts and ideas, remind-cli gives AI agents the tools to navigate it efficiently.
---

### Core Commands & Workflow

1. **Initialization & Ingestion**
   * `remind init [project_name]`: Initializes a new project in the Vault, creating the base `map.index` JSON and unique project hash.
   * `remind import`: Scans the global `import/` folder, processes raw exports (CSV/JSON), and generates temporary `_Inbox_` Markdown files grouped by session.

2. **Writing & Modifying**
   * `remind write [logical_path] --file <temp_file_path>`: Creates a new document (or overwrites one if given the full logical path) at the location specified using the content of a temporary file. It automatically rebuilds the index afterwards. 
   
   **Example (PowerShell):**
   1. `$tmp = New-TemporaryFile`
   2. `Set-Content -Path $tmp.FullName -Value "Your multi-line content" -Encoding UTF8`
   3. `remind write jobalerts84e --file $tmp.FullName`
   4. `Remove-Item $tmp.FullName`
   
   * `remind append [logical_path] --file <temp_file_path>`: Appends content from a temporary file to the end of a document. It automatically rebuilds the index afterwards. 

3. **Indexing**
   * `remind index [project_hash]`: Scans the folder structure and rebuilds `map.index` which is a map or table of contents of every notebook. After reorganising .md files it must be executed but not when using the write or append command.

4. **Querying & Navigation (Read-Only)**
   * `remind map [project_hash]`: Command that returns the index of a given notebook or logical node. To obtain the project hash first you must run it without arguments to get a list of all notebooks available.
   * `remind me [full_logical_path]`: Command that returns the content of a text document or specific parts from it. You must provide a full path to the document or node without skipping any levels. Supports brace expansion for targeting multiple paragraphs.
   
   **Example (PowerShell):**
   1. `remind me testprojea1b.fe.spec.{fsadx1a,fsbol2b}`

   * `remind tag [project_hash] list`: Returns a list of all existing tags sorted by popularity.
   * `remind tag [project_hash] <tag>`: Performs a cross-sectional search returning logical paths that contain that specific tag.
