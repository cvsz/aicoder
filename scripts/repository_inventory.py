#!/usr/bin/env python3
"""Generate a deterministic, dependency-free repository inventory.

The report is intentionally static: it parses Python source with ``ast`` and
searches text files without importing project modules or requiring provider
credentials. Output is JSON so CI and documentation tooling can compare it.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

TEXT_SUFFIXES = {
    ".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt", ".ini", ".cfg",
    ".html", ".css", ".js", ".ts", ".tsx", ".sh", ".ps1", ".bat",
}
IGNORED_PARTS = {
    ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__",
    "build", "dist", ".venv", "venv", "node_modules",
}
PROVIDER_MODULES = {"anthropic", "openai", "google.generativeai", "cohere"}
CREDENTIAL_PATTERNS = (
    re.compile(r"ANTHROPIC_API_KEY"),
    re.compile(r"OPENAI_API_KEY"),
    re.compile(r"GOOGLE_API_KEY"),
    re.compile(r"api[_-]?key", re.IGNORECASE),
)
RISK_PATTERNS = {
    "todo": re.compile(r"\bTODO\b"),
    "fixme": re.compile(r"\bFIXME\b"),
    "hack": re.compile(r"\bHACK\b"),
    "not_implemented": re.compile(r"NotImplemented(?:Error)?"),
    "shell_true": re.compile(r"shell\s*=\s*True"),
    "broad_ignore": re.compile(r"(?:noqa\b|type:\s*ignore\b|eslint-disable)"),
    "hardcoded_localhost": re.compile(r"https?://(?:localhost|127\.0\.0\.1)"),
}


@dataclass(frozen=True)
class PythonFile:
    path: str
    imports: tuple[str, ...]
    functions: tuple[str, ...]
    classes: tuple[str, ...]
    argparse_dests: tuple[str, ...]
    args_reads: tuple[str, ...]
    provider_imports: tuple[str, ...]
    syntax_error: str | None


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        yield path


def dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def string_arg(call: ast.Call, position: int = 0) -> str | None:
    if len(call.args) <= position:
        return None
    value = call.args[position]
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def parse_python(path: Path, root: Path) -> PythonFile:
    rel = path.relative_to(root).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)
    except (UnicodeDecodeError, SyntaxError) as exc:
        return PythonFile(rel, (), (), (), (), (), (), str(exc))

    imports: set[str] = set()
    functions: set[str] = set()
    classes: set[str] = set()
    argparse_dests: set[str] = set()
    args_reads: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "args":
            args_reads.add(node.attr)
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name and name.endswith("add_argument"):
                explicit_dest = next(
                    (kw.value.value for kw in node.keywords
                     if kw.arg == "dest" and isinstance(kw.value, ast.Constant)
                     and isinstance(kw.value.value, str)),
                    None,
                )
                flag = string_arg(node)
                if explicit_dest:
                    argparse_dests.add(explicit_dest)
                elif flag:
                    argparse_dests.add(flag.lstrip("-").replace("-", "_"))

    provider_imports = sorted(
        imp for imp in imports
        if any(imp == provider or imp.startswith(provider + ".") for provider in PROVIDER_MODULES)
    )
    return PythonFile(
        path=rel,
        imports=tuple(sorted(imports)),
        functions=tuple(sorted(functions)),
        classes=tuple(sorted(classes)),
        argparse_dests=tuple(sorted(argparse_dests)),
        args_reads=tuple(sorted(args_reads)),
        provider_imports=tuple(provider_imports),
        syntax_error=None,
    )


def scan_text(path: Path, root: Path) -> dict[str, list[int]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {}
    hits: dict[str, list[int]] = defaultdict(list)
    for number, line in enumerate(text.splitlines(), 1):
        for name, pattern in RISK_PATTERNS.items():
            if pattern.search(line):
                hits[name].append(number)
        if any(pattern.search(line) for pattern in CREDENTIAL_PATTERNS):
            hits["credential_reference"].append(number)
    return dict(sorted(hits.items()))


def build_inventory(root: Path) -> dict[str, object]:
    files = list(iter_files(root))
    python = [parse_python(path, root) for path in files if path.suffix == ".py"]
    text_hits = {
        path.relative_to(root).as_posix(): hits
        for path in files
        if path.suffix in TEXT_SUFFIXES and (hits := scan_text(path, root))
    }

    extensions = Counter(path.suffix or "<none>" for path in files)
    declared = set().union(*(set(item.argparse_dests) for item in python)) if python else set()
    read = set().union(*(set(item.args_reads) for item in python)) if python else set()
    providers = {
        item.path: list(item.provider_imports) for item in python if item.provider_imports
    }

    return {
        "schema_version": 1,
        "root": root.resolve().as_posix(),
        "summary": {
            "files": len(files),
            "python_files": len(python),
            "test_files": sum(1 for item in python if item.path.startswith("tests/")),
            "syntax_errors": sum(1 for item in python if item.syntax_error),
            "provider_import_files": len(providers),
            "credential_reference_files": sum(
                1 for hits in text_hits.values() if "credential_reference" in hits
            ),
        },
        "extensions": dict(sorted(extensions.items())),
        "entry_points": {
            "main_py": (root / "main.py").exists(),
            "tui_py": (root / "tui.py").exists(),
            "web_backend": (root / "webapp/backend/server.py").exists(),
            "workflows": sorted(
                path.relative_to(root).as_posix()
                for path in files if path.parts[:2] == (".github", "workflows")
            ),
        },
        "cli": {
            "declared_destinations": sorted(declared),
            "read_destinations": sorted(read),
            "declared_not_directly_read": sorted(declared - read),
            "read_not_declared": sorted(read - declared),
        },
        "provider_imports": providers,
        "risk_hits": text_hits,
        "python": [asdict(item) for item in python],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true", help="exit non-zero on syntax errors")
    args = parser.parse_args()

    inventory = build_inventory(args.root.resolve())
    payload = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

    if args.check and inventory["summary"]["syntax_errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
