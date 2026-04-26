import importlib.resources
import os
import sys
import pytest
import argparse
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


def get_subparser(parser, name):
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    return subparsers_action.choices[name]


def test_index_parser_takes_no_positional_args():
    parser = main.build_parser()

    args = parser.parse_args(["index"])

    assert args.command == "index"
    assert args.func is main.handle_index

    with pytest.raises(SystemExit):
        parser.parse_args(["index", "project_hash"])


def test_write_parser_uses_actual_file_name_and_temp_file_positionals():
    parser = main.build_parser()

    args = parser.parse_args(["write", "projhash.ab", "Meeting Notes", "temp.txt"])

    assert args.command == "write"
    assert args.path == "projhash.ab"
    assert args.file_name == "Meeting Notes"
    assert args.temp_file == "temp.txt"
    assert args.func is main.handle_write


def test_write_help_mentions_actual_file_name_and_no_file_flag():
    parser = main.build_parser()
    write_help = get_subparser(parser, "write").format_help()

    assert "actual file name" in write_help.lower()
    assert "generated slug" in write_help.lower()
    assert ".md extension" in write_help.lower()
    assert "--file" not in write_help


def test_index_help_mentions_no_args():
    parser = main.build_parser()
    index_help = get_subparser(parser, "index").format_help()

    assert "takes no positional arguments" in index_help.lower()


def test_handle_write_passes_actual_file_name_to_execute_write(tmp_path, monkeypatch):
    temp_file = tmp_path / "content.txt"
    temp_file.write_text("hello world", encoding="utf-8")

    captured = {}
    monkeypatch.setattr(main, "get_vault_path", lambda: tmp_path / "vault")

    def fake_execute_write(vault_path, logical_path, content, mode="w", file_name=None):
        captured["vault_path"] = vault_path
        captured["logical_path"] = logical_path
        captured["file_name"] = file_name
        captured["content"] = content
        captured["mode"] = mode

    monkeypatch.setattr(main, "execute_write", fake_execute_write)

    main.handle_write(
        SimpleNamespace(path="projhash.ab", file_name="Meeting Notes", temp_file=str(temp_file))
    )

    assert captured["logical_path"] == "projhash.ab"
    assert captured["file_name"] == "Meeting Notes"
    assert captured["content"] == "hello world"
    assert captured["mode"] == "w"


def test_append_parser_keeps_file_flag_interface():
    parser = main.build_parser()

    args = parser.parse_args(["append", "projhash.file", "--file", "temp.txt"])

    assert args.command == "append"
    assert args.path == "projhash.file"
    assert args.file == "temp.txt"
    assert args.func is main.handle_append


def test_append_help_keeps_file_flag():
    parser = main.build_parser()
    append_help = get_subparser(parser, "append").format_help()

    assert "--file" in append_help
    assert "actual file name" not in append_help.lower()