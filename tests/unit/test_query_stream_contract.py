"""
Streaming query contract tests for Atlas server.
"""

from __future__ import annotations

import json

from apps.server import server


def test_sse_event_encodes_named_json_frame() -> None:
    frame = server._sse_event("chunk", {"content": "hello", "value": float("nan")})

    assert frame.startswith("event: chunk\n")
    assert frame.endswith("\n\n")

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload == {"content": "hello", "value": None}


def test_stream_text_chunks_preserve_content_order() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"

    chunks = server._stream_text_chunks(text, chunk_size=7)

    assert chunks == ["abcdefg", "hijklmn", "opqrstu", "vwxyz"]
    assert "".join(chunks) == text


def test_stream_route_is_registered() -> None:
    paths = server._collect_route_paths()

    assert "/query/stream" in paths
