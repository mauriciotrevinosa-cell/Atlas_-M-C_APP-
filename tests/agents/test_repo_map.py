from pathlib import Path

from atlas.core.ai_assistant import build_repo_map


def test_build_repo_map_extracts_python_imports_and_symbols(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "alpha.py").write_text(
        "import os\nfrom atlas.core import thing\n\nclass Alpha:\n    pass\n\ndef run():\n    return 1\n",
        encoding="utf-8",
    )

    repo_map = build_repo_map(tmp_path)
    payload = repo_map.to_dict()

    assert payload["file_count"] == 1
    node = payload["files"][0]
    assert node["path"] == "pkg/alpha.py"
    assert node["language"] == "python"
    assert node["imports"] == ["os", "atlas"]
    assert node["symbols"] == ["Alpha", "run"]
    assert payload["modules"][0]["module"] == "pkg"


def test_build_repo_map_extracts_js_imports_and_symbols(tmp_path: Path):
    (tmp_path / "app.tsx").write_text(
        "import React from 'react';\n"
        "import { x } from './local';\n"
        "export function Widget() { return null; }\n"
        "const helper = () => 1;\n",
        encoding="utf-8",
    )

    repo_map = build_repo_map(tmp_path)
    node = repo_map.to_dict()["files"][0]

    assert node["language"] == "typescript-react"
    assert "react" in node["imports"]
    assert "./local" in node["imports"]
    assert "Widget" in node["symbols"]
    assert "helper" in node["symbols"]


def test_build_repo_map_ignores_node_modules(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("const ignored = 1;", encoding="utf-8")
    (tmp_path / "main.js").write_text("const included = 1;", encoding="utf-8")

    repo_map = build_repo_map(tmp_path)
    paths = [node.path for node in repo_map.files]

    assert paths == ["main.js"]


def test_repo_map_renders_mermaid_module_edges(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "utils").mkdir()
    (tmp_path / "pkg" / "alpha.py").write_text("import utils\n", encoding="utf-8")
    (tmp_path / "utils" / "beta.py").write_text("def helper():\n    return 1\n", encoding="utf-8")

    repo_map = build_repo_map(tmp_path)
    mermaid = repo_map.to_mermaid()

    assert mermaid.startswith("flowchart LR")
    assert "pkg[pkg] -->|1| utils[utils]" in mermaid
