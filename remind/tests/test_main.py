import importlib.resources
import os
import sys
from pathlib import Path
from types import SimpleNamespace


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import remind.main as main


def test_handle_install_overwrites_existing_skill_file(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    agent_dir = home_dir / ".agents" / "skills" / "remind"
    agent_dir.mkdir(parents=True)

    skill_file = agent_dir / "SKILL.md"
    skill_file.write_text("old skill version", encoding="utf-8")

    vault_dir = tmp_path / "vault"
    monkeypatch.setattr(main.Path, "home", lambda: home_dir)
    monkeypatch.setattr(main, "get_vault_path", lambda: vault_dir)

    expected_skill = (
        importlib.resources.files("remind").joinpath("SKILL.md").read_bytes()
    )

    main.handle_install(SimpleNamespace())

    assert skill_file.read_bytes() == expected_skill
    assert vault_dir.exists()