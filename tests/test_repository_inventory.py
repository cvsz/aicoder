from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).parents[1] / "scripts" / "repository_inventory.py"
    spec = importlib.util.spec_from_file_location("repository_inventory", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_detects_cli_provider_and_risk_patterns(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "tests").mkdir()
    (tmp_path / "main.py").write_text(
        "import anthropic\n"
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--api-url')\n"
        "args = p.parse_args([])\n"
        "print(args.api_url)\n",
        encoding="utf-8",
    )
    (tmp_path / "worker.py").write_text(
        "import subprocess\n"
        "subprocess.run('echo ok', shell=True)\n"
        "# TODO harden this\n"
        "KEY = 'ANTHROPIC_API_KEY'\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_example.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    report = module.build_inventory(tmp_path)

    assert report["summary"]["python_files"] == 3
    assert report["summary"]["test_files"] == 1
    assert report["summary"]["provider_import_files"] == 1
    assert report["cli"]["declared_destinations"] == ["api_url"]
    assert report["cli"]["read_not_declared"] == []
    assert report["provider_imports"] == {"main.py": ["anthropic"]}
    assert report["risk_hits"]["worker.py"]["shell_true"] == [2]
    assert report["risk_hits"]["worker.py"]["todo"] == [3]
    assert report["risk_hits"]["worker.py"]["credential_reference"] == [4]


def test_inventory_is_json_serializable_and_deterministic(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "b.py").write_text("class B: pass\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("def a(): return 1\n", encoding="utf-8")

    first = module.build_inventory(tmp_path)
    second = module.build_inventory(tmp_path)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert [item["path"] for item in first["python"]] == ["a.py", "b.py"]


def test_check_mode_can_identify_syntax_errors(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    report = module.build_inventory(tmp_path)

    assert report["summary"]["syntax_errors"] == 1
    assert report["python"][0]["syntax_error"]
