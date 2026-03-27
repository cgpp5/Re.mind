---
name: remind-cli
description: This skill allows you to access and interact with the Re.mind Vault. The Re.mind Vault is an offline curated Markdown-based knowledge repository that helps users organize their thoughts and ideas, remind-cli gives AI agents the tools to navigate it efficiently.
---

### System Architecture & Principles
* **Source of Truth:** Knowledge lives entirely in human-editable `.md` files.
* **Strict Separation:** The user owns the content; the CLI manages the logical structure; the AI uses the CLI to read injected context but never directly accesses the filesystem.
* **Project Identity:** Every project gets a 12-character unique hash (e.g., `testprojea1b`).
* **Semantic Navigation (Slugs):** Directories and files use dot notation namespaces (e.g., `ds`, `main`, `spec`) instead of raw paths.

### Core Commands & Workflow

1. **Initialization & Ingestion**
   * `remind init [project_name]`: Initializes a new project in the Vault, creating the base `map.index` JSON and unique project hash.
   * `remind import`: Scans the global `import/` folder, processes raw exports (CSV/JSON), and generates temporary `_Inbox_` Markdown files grouped by session.

2. **Indexing (Crucial Step)**
   * `remind index [project_hash]`: Scans the folder structure, compiles `.md` files, extracts inline tags (e.g., `#testing`), updates exact line numbers in JSON sidecars, and rebuilds `map.index`. 
   * *Rule:* Must be executed whenever Markdown files are manually edited or reorganized.

3. **Querying & Navigation (Read-Only)**
   * `remind map [logical_path]`: Universal command to query the knowledge structure. Used without arguments, it returns the global Vault state.
   * `remind tag <project_hash> list`: Returns a table of all existing tags sorted by popularity.
   * `remind tag <project_hash> <tag>`: Performs a cross-sectional search ignoring folders, returning logical paths that contain the specified tag.
   * `remind me <paths>`: The only command that fetches exact text from the hard drive. Resolves hierarchy via JSON and outputs the exact content of nodes. Supports brace expansion (e.g., `remind me testprojea1b.fe.spec.{fsadx1a,fsbol2b}`).

### Common Issues & Best Practices
* **Missing content:** If the user cannot find recent changes, remind them to run `remind index` so the engine updates the sidecars and `map.index`.
* **Brace Expansion:** The CLI handles `{}` internally using regex in Python, ensuring cross-platform support regardless of terminal (Bash/Zsh vs CMD/PowerShell). 
* **Inbox Curation:** Remind users that imported files are temporary (`_Inbox_`); they must curate and move them to actual project folders before re-indexing.