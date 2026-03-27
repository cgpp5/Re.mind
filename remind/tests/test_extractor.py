import os
import sys
import json
import pytest
from pathlib import Path

# Añadimos la ruta raíz para poder importar el módulo core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.extractor import find_project_in_vault, extract_node, run_extractor

# ==========================================
# FIXTURES (ENTORNO DE PRUEBA)
# ==========================================

@pytest.fixture
def mock_vault(tmp_path):
    """
    Crea un Vault temporal aislado e inyecta los datos exactos
    del documento "Clarifying Playwrights GeoIP Capabilities".
    """
    vault_dir = tmp_path / "Re.mind vault"
    project_dir = vault_dir / "job_alerts_project"
    project_dir.mkdir(parents=True)
    
    # 1. Crear el map.index con el hash 'jobalerts84e' en .remind
    remind_dir = project_dir / ".remind"
    remind_dir.mkdir()
    sidecars_dir = remind_dir / "sidecars"
    sidecars_dir.mkdir()

    map_index_content = {
      "jobalerts84e": {
        "_meta": {
          "project_name": "job-alerts",
          "indexed_at": "2026-03-25T17:27:01Z"
        },
        "_tags": {},
        "clar": {
          "_file": "Clarifying Playwrights GeoIP Capabilities.md",
          "clari8a": { "_title": "Clarifying Playwright's GeoIP Capabilities" },
          "ai202e6": { "_title": "🗣️ Ai *( 2026-02-21 10:51 )*" },
          "whatp7b": { "_title": "What Playwright actually supports (explicit only)" }
        }
      }
    }
    with open(remind_dir / "map.index", "w", encoding="utf-8") as f:
        json.dump(map_index_content, f)

    # 2. Crear el archivo Markdown (Mock parcial basado en tus datos)
    md_content = """# Clarifying Playwright's GeoIP Capabilities
> **Imported at:** 2026-03-25 17:04:04 UTC
> **Source file:** copilot-activity-history.csv

---

### 🗣️ Ai *( 2026-02-21 10:51 )*

That sentence is **not a real Playwright feature**.
What you’re seeing is either:
- Documentation from a **third‑party wrapper** around Playwright

---

### What Playwright actually supports (explicit only)

Playwright requires **manual, explicit configuration** for all of these:
- **Timezone** — `timezoneId`
- **Locale** — `locale`
"""
    # Guardamos forzando saltos de línea LF por simplicidad en el test
    with open(project_dir / "Clarifying Playwrights GeoIP Capabilities.md", "w", encoding="utf-8", newline='\n') as f:
        f.write(md_content)

    # 3. Crear el Sidecar JSON con los rangos mapeados al mock anterior
    # (Ajustamos las líneas al string md_content de arriba)
    sidecar_content = {
      "schema": "doc-cli.sidecar.v1",
      "blocks": {
        "clari8a": {
          "type": "heading",
          "range": { "start_line": 1, "end_line": 6 }
        },
        "ai202e6": {
          "type": "heading",
          "range": { "start_line": 7, "end_line": 14 }
        },
        "whatp7b": {
          "type": "heading",
          "range": { "start_line": 15, "end_line": 21 }
        }
      }
    }
    with open(sidecars_dir / "jobalerts84e.clar.sidecar.json", "w", encoding="utf-8") as f:
        json.dump(sidecar_content, f)

    return vault_dir


# ==========================================
# TESTS
# ==========================================

def test_find_project_in_vault_success(mock_vault):
    """Prueba que el buscador de proyectos localiza la carpeta correcta a través del hash."""
    project_dir, map_data = find_project_in_vault(mock_vault, "jobalerts84e")
    
    assert project_dir is not None
    assert project_dir.name == "job_alerts_project"
    
    # Comprobamos directamente las llaves internas, ya que el extractor nos devuelve el payload limpio
    assert "_meta" in map_data
    assert map_data["_meta"]["project_name"] == "job-alerts"

def test_find_project_in_vault_not_found(mock_vault):
    """Prueba el comportamiento cuando se pide un hash de proyecto que no existe."""
    project_dir, map_data = find_project_in_vault(mock_vault, "hashinventado99")
    
    assert project_dir is None
    assert map_data is None

def test_extract_node_valid_block(mock_vault, capsys):
    """Prueba la extracción precisa de un único epígrafe/bloque usando su sidecar."""
    # Extraemos el bloque "What Playwright actually supports"
    extract_node(mock_vault, "jobalerts84e.clar.whatp7b")
    
    # Capturamos lo que el extractor imprime por consola
    captured = capsys.readouterr().out
    
    # Verificaciones
    assert "SOURCE: jobalerts84e.clar.whatp7b" in captured
    assert "### What Playwright actually supports" in captured
    assert "- **Timezone** — `timezoneId`" in captured
    
    # NO debería contener texto de otros bloques
    assert "Clarifying Playwright's GeoIP Capabilities" not in captured
    assert "That sentence is **not a real Playwright feature**" not in captured

def test_extract_node_full_file(mock_vault, capsys):
    """Prueba la extracción de un archivo completo (cuando no se especifica epígrafe final)."""
    extract_node(mock_vault, "jobalerts84e.clar")
    
    captured = capsys.readouterr().out
    
    # Al pedir todo el archivo, debería tener tanto la cabecera como el último bloque
    assert "Clarifying Playwright's GeoIP Capabilities" in captured
    assert "### What Playwright actually supports" in captured

def test_extract_node_invalid_project(mock_vault, capsys):
    """Prueba el manejo de errores: Hash de proyecto inexistente."""
    extract_node(mock_vault, "error123.clar.whatp7b")
    captured = capsys.readouterr().out
    assert "[-] Error: Project with hash 'error123' not found in vault." in captured

def test_extract_node_invalid_block(mock_vault, capsys):
    """Prueba el manejo de errores: Epígrafe inexistente en el índice."""
    extract_node(mock_vault, "jobalerts84e.clar.bloquefalso")
    captured = capsys.readouterr().out
    assert "[-] Error: Block 'bloquefalso' not found in file 'Clarifying Playwrights GeoIP Capabilities.md'." in captured

def test_run_extractor_multiple_paths(mock_vault, capsys):
    """Prueba la ejecución en lote (array de rutas) como lo haría el enrutador de sintaxis {a,b}."""
    paths = [
        "jobalerts84e.clar.clari8a",  # El primer bloque (título)
        "jobalerts84e.clar.whatp7b"   # El tercer bloque
    ]
    
    run_extractor(mock_vault, paths)
    captured = capsys.readouterr().out
    
    # Debe haber procesado e impreso ambas fuentes por separado
    assert "SOURCE: jobalerts84e.clar.clari8a" in captured
    assert "SOURCE: jobalerts84e.clar.whatp7b" in captured