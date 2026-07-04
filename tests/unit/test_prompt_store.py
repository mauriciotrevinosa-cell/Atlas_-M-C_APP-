from __future__ import annotations

import pytest

from atlas.services.llm import PromptStore, PromptTemplateInfo


def test_prompt_store_strict_render_and_manifest(tmp_path):
    prompt_path = tmp_path / "planner.md"
    prompt_path.write_text(
        "Objective: {OBJETIVO}\nContext: {CONTEXTO}\n",
        encoding="utf-8",
    )
    store = PromptStore(prompts_dir=tmp_path)

    rendered = store.render_strict("planner", OBJETIVO="Build", CONTEXTO="Atlas")
    manifest = store.get_manifest("planner")

    assert rendered == "Objective: Build\nContext: Atlas\n"
    assert isinstance(manifest, PromptTemplateInfo)
    assert manifest.name == "planner"
    assert manifest.placeholders == ["CONTEXTO", "OBJETIVO"]
    assert manifest.cached is True
    assert manifest.to_dict()["line_count"] == 2


def test_prompt_store_strict_render_rejects_missing_placeholder(tmp_path):
    (tmp_path / "reviewer.md").write_text("Review {CODE} for {MODULE}", encoding="utf-8")
    store = PromptStore(prompts_dir=tmp_path)

    with pytest.raises(ValueError, match="Missing prompt placeholders"):
        store.render_strict("reviewer", CODE="x = 1")


def test_prompt_store_lists_manifests(tmp_path):
    (tmp_path / "a.md").write_text("A {ONE}", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B {TWO}", encoding="utf-8")
    (tmp_path / "_hidden.md").write_text("hidden", encoding="utf-8")
    store = PromptStore(prompts_dir=tmp_path)

    manifests = store.list_manifests()

    assert [item.name for item in manifests] == ["a", "b"]
    assert {item.placeholders[0] for item in manifests} == {"ONE", "TWO"}
