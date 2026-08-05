from __future__ import annotations

import html
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

_TAG = re.compile(r"<[^>]+>")
_PARA_END = re.compile(r"</w:p>")


def _docx_to_text(path: Path) -> str:
    """Đọc .docx (là file zip) — nhanh, không phụ thuộc textutil/iCloud."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = _PARA_END.sub("\n", xml)  # mỗi đoạn <w:p> thành 1 dòng
    text = _TAG.sub("", xml)
    return html.unescape(text)


def _doc_to_text(path: Path) -> str:
    """Đọc .doc (Word cũ) qua textutil của macOS."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.txt")
        subprocess.run(
            ["textutil", "-convert", "txt", "-encoding", "UTF-8", "-output", out, str(path)],
            check=True,
            timeout=300,
        )
        return Path(out).read_text(encoding="utf-8", errors="replace")


def to_text(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        return _docx_to_text(path)
    if suffix == ".doc":
        return _doc_to_text(path)
    raise ValueError(f"Định dạng không hỗ trợ: {path.suffix}")
