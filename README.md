# 🧠 Re.mind

**Re.mind is a context management CLI that lets users funnel conversational and technical data into a local Markdown vault, empowering LLMs to ground their responses by extracting exactly the information they need.**

[![PyPI version](https://img.shields.io/pypi/v/remind-cli.svg)](https://pypi.org/project/remind-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/re.mind.svg)](https://pypi.org/project/re.mind/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

It transforms raw conversational data from ChatGPT, Claude, Gemini or Copilot into structured documents that can then be edited with tools like ObsidianMD. It creates a semantic index that AI agents can use to query documentation with millimeter precision without the need to copy and paste files to multiple locations.

---

## 🚀 Key Features

* **100% Local:** Your data lives on your hard drive (`Re.mind vault/`).
* **Simplicity:** Based on Markdown and 100% compatible with Obsidian.
* **Semantic Navigation (Dot Notation):** Access any heading or knowledge block using efficient logical paths (`project.folder.file.heading`).
* **Hybrid Tagging System:** Native support for inline `#hashtags` that are automatically indexed globally.
* **Context Friendly:** Designed for an LLM to extract exact context blocks on demand, reducing token consumption.

---

## 📦 Installation

Re.mind is written in Python and distributed via PyPI. It requires Python 3.9 or higher.

```bash
pip install re.mind
```

---

## 🛠️ Workflow and Commands

The core loop of Re.mind is encapsulated in writing (ingestion and indexing) and reading (querying and extraction).

### 1. Data Management (Write)

* **`remind init <name>`**
  Initializes a new project notebook in your Vault. Creates the technical structure (`.remind/`) and generates the unique project hash.
  ```bash
  $ remind init "Trading Bot"
  ```

* **`remind import`**
  Scans the global `import/` folder looking for `.csv` or `.json` exports (Google Takeout, Copilot, Claude or OpenAI) and generates clean, chronologically structured Markdown notebooks in a temporary inbox (`_Inbox_`). Smartly avoids duplicates.
  ```bash
  $ remind import
  ```

* **`remind index [project_hash]`**
  The core engine. Scans the folder structure, detects blocks, extracts inline hashtags (e.g., `#architecture`), and rebuilds the semantic map (`map.index`) and the auxiliary coordinate files (`sidecars`). 
  *Note: Always run this after manually reorganizing or editing your Markdown files in Obsidian.*
  ```bash
  $ remind index tradinbot4a2
  ```

### 2. Query and Extraction (Read)

* **`remind map [logical_path]`**
  Displays a visual tree with the structure of the indexed knowledge. With no arguments, it shows the global state of the Vault.
  ```bash
  $ remind map tradinbot4a2.fe
  ```

* **`remind tag <hash> list`** | **`remind tag <hash> <tag>`**
  Transversal search system. Lists all tags in a project sorted by popularity, or searches for a specific tag, returning the exact paths of the documents that contain it.
  ```bash
  $ remind tag tradinbot4a2 list
  $ remind tag tradinbot4a2 architecture
  ```

* **`remind me <paths>`**
  The key command for knowledge extraction. Breaks through the index layer to go directly to the hard drive and spit out the exact text via the terminal. Supports brace expansion `{}` syntax to extract multiple nodes simultaneously.
  ```bash
  $ remind me tradinbot4a2.fe.spec.{fsadx1a,fsbol2b}
  ```

---

## 🏗️ Internal Architecture

Re.mind abstracts complexity through a system of short names (Slugs) and a coordinate map (Sidecars).

Every Markdown file has a hidden twin JSON file in the `.remind/sidecars/` folder. This file acts as a spatial coordinate system: it maps the exact start and end lines of every heading and the tags the document contains, allowing the `remind me` command to extract surgical snippets without having to parse heavy text files in real-time.

---

## 🤝 Contributing

If you want to collaborate, clone the repository and install it in editable mode:

```bash
git clone https://github.com/cgpp5/Re.mind.git
cd Re.mind
pip install -e .
```

---

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0. See the `LICENSE` file for details.
