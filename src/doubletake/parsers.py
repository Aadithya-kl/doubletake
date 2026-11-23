"""Parser adapters: 'what the model reads'.

Built-ins cover common Python ingestion libraries. Users add their own stack
with --parser 'name=shell command {file}' or --parser-py 'module:function'.
"""

from __future__ import annotations

import importlib
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ALL_FORMATS = ("pdf", "docx", "xlsx", "pptx", "html", "eml")


@dataclass
class Parser:
    name: str
    formats: set[str]
    fn: Callable[[Path], str]
    available: bool = True
    note: str = ""
    custom: bool = False
    use_in_scan: bool = True  # raw markup is noise when diffing against the rendered page


def _pypdf(p: Path) -> str:
    from pypdf import PdfReader

    r = PdfReader(str(p))
    return "\n".join((pg.extract_text() or "") for pg in r.pages)


def _pypdf_meta(p: Path) -> str:
    """pypdf text + document info, as many RAG loaders attach metadata."""
    from pypdf import PdfReader

    r = PdfReader(str(p))
    meta = " ".join(str(v) for v in (r.metadata or {}).values())
    return _pypdf(p) + "\n" + meta


def _pdfplumber(p: Path) -> str:
    import pdfplumber

    with pdfplumber.open(str(p)) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def _pdfminer(p: Path) -> str:
    from pdfminer.high_level import extract_text

    return extract_text(str(p))


def _pdftotext(p: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, timeout=60).stdout


def _markitdown(p: Path) -> str:
    from markitdown import MarkItDown

    return MarkItDown().convert(str(p)).text_content


def _python_docx(p: Path) -> str:
    from docx import Document

    return "\n".join(par.text for par in Document(str(p)).paragraphs)


def _python_docx_meta(p: Path) -> str:
    from docx import Document

    d = Document(str(p))
    cp = d.core_properties
    meta = " ".join(filter(None, [cp.title, cp.subject, cp.keywords, cp.comments]))
    return "\n".join(par.text for par in d.paragraphs) + "\n" + meta


def _soffice_txt(p: Path) -> str:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text (encoded):UTF8", "--outdir", td, str(p)],
                       capture_output=True, timeout=120)
        out = Path(td) / (p.stem + ".txt")
        return out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""


def _bs4(p: Path) -> str:
    from bs4 import BeautifulSoup

    return BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser").get_text(" ")


def _bs4_strip(p: Path) -> str:
    """bs4 after dropping script/style - the 'careful' common pattern."""
    from bs4 import BeautifulSoup

    s = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in s(["script", "style"]):
        t.decompose()
    return s.get_text(" ")


def _openpyxl_all(p: Path) -> str:
    """Every cell of every sheet - what most 'load the spreadsheet' code does."""
    from openpyxl import load_workbook

    wb = load_workbook(str(p), data_only=True)
    out = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            out.append(" ".join(str(v) for v in row if v is not None))
    return "\n".join(out)


def _openpyxl_visible(p: Path) -> str:
    """Careful baseline: skip hidden sheets, rows and columns."""
    from openpyxl import load_workbook

    wb = load_workbook(str(p), data_only=True)
    out = []
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            continue
        for row in ws.iter_rows():
            for c in row:
                if c.value is None or ws.row_dimensions[c.row].hidden or ws.column_dimensions[c.column_letter].hidden:
                    continue
                out.append(str(c.value))
    return "\n".join(out)


def _openpyxl_comments(p: Path) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(str(p))
    return "\n".join(c.comment.text for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.comment)


def _python_pptx(p: Path, notes: bool = False) -> str:
    from pptx import Presentation

    out = []
    for slide in Presentation(str(p)).slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
        if notes and slide.has_notes_slide:
            out.append(slide.notes_slide.notes_text_frame.text)
    return "\n".join(out)


def _email_plain(p: Path) -> str:
    """Prefer text/plain, fall back to stripped HTML - the common pattern."""
    import email
    from email import policy

    from bs4 import BeautifulSoup

    m = email.message_from_bytes(p.read_bytes(), policy=policy.default)
    body = m.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    text = body.get_content()
    if body.get_content_type() == "text/html":
        text = BeautifulSoup(text, "html.parser").get_text(" ")
    return f"Subject: {m['subject']}\n{text}"


def _email_html(p: Path) -> str:
    """Prefer text/html (what the human sees), stripped with bs4."""
    import email
    from email import policy

    from bs4 import BeautifulSoup

    m = email.message_from_bytes(p.read_bytes(), policy=policy.default)
    body = m.get_body(preferencelist=("html", "plain"))
    if body is None:
        return ""
    text = body.get_content()
    if body.get_content_type() == "text/html":
        text = BeautifulSoup(text, "html.parser").get_text(" ")
    return f"Subject: {m['subject']}\n{text}"


def _email_all(p: Path) -> str:
    """All headers plus every text part - what 'dump the email into the prompt' does."""
    import email
    from email import policy

    m = email.message_from_bytes(p.read_bytes(), policy=policy.default)
    head = "\n".join(f"{k}: {v}" for k, v in m.items())
    parts = [part.get_content() for part in m.walk() if part.get_content_maintype() == "text"]
    return head + "\n" + "\n".join(parts)


def _raw(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _has(mod: str) -> bool:
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def builtin_parsers() -> list[Parser]:
    soffice = shutil.which("soffice") is not None
    return [
        Parser("pypdf", {"pdf"}, _pypdf, _has("pypdf")),
        Parser("pypdf+metadata", {"pdf"}, _pypdf_meta, _has("pypdf")),
        Parser("pdfplumber", {"pdf"}, _pdfplumber, _has("pdfplumber")),
        Parser("pdfminer.six", {"pdf"}, _pdfminer, _has("pdfminer")),
        Parser("pdftotext", {"pdf"}, _pdftotext, shutil.which("pdftotext") is not None),
        Parser("markitdown", {"pdf", "docx", "xlsx", "pptx", "html"}, _markitdown, _has("markitdown")),
        Parser("python-docx", {"docx"}, _python_docx, _has("docx")),
        Parser("python-docx+metadata", {"docx"}, _python_docx_meta, _has("docx")),
        Parser("libreoffice-txt", {"docx"}, _soffice_txt, soffice),
        Parser("openpyxl (all cells)", {"xlsx"}, _openpyxl_all, _has("openpyxl")),
        Parser("openpyxl (visible only)", {"xlsx"}, _openpyxl_visible, _has("openpyxl"),
               note="skips hidden sheets/rows/columns - the careful baseline"),
        Parser("openpyxl (comments)", {"xlsx"}, _openpyxl_comments, _has("openpyxl")),
        Parser("python-pptx", {"pptx"}, _python_pptx, _has("pptx")),
        Parser("python-pptx+notes", {"pptx"}, lambda p: _python_pptx(p, notes=True), _has("pptx")),
        Parser("email (plain preferred)", {"eml"}, _email_plain, _has("bs4")),
        Parser("email (html preferred)", {"eml"}, _email_html, _has("bs4")),
        Parser("email (all parts+headers)", {"eml"}, _email_all, True, use_in_scan=False),
        Parser("bs4.get_text", {"html"}, _bs4, _has("bs4")),
        Parser("bs4 (strip script/style)", {"html"}, _bs4_strip, _has("bs4")),
        Parser("raw-html", {"html"}, _raw, True, note="what an agent sees if it fetches the page source", use_in_scan=False),
    ]


def command_parser(spec: str, formats: set[str] | None = None) -> Parser:
    """'name=cmd args {file}' -> Parser that returns the command's stdout."""
    if "=" not in spec:
        raise ValueError("--parser expects NAME=COMMAND (use {file} for the path)")
    name, cmd = spec.split("=", 1)

    def run(p: Path) -> str:
        args = [a.replace("{file}", str(p)) for a in shlex.split(cmd)]
        if not any("{file}" in a for a in shlex.split(cmd)):
            args.append(str(p))
        r = subprocess.run(args, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip()[:300] or f"exit {r.returncode}")
        return r.stdout

    return Parser(name.strip(), formats or set(ALL_FORMATS), run, custom=True)


def python_parser(spec: str, formats: set[str] | None = None) -> Parser:
    """'package.module:function' where function(path: str) -> str."""
    mod, _, func = spec.partition(":")
    fn = getattr(importlib.import_module(mod), func)
    return Parser(spec, formats or set(ALL_FORMATS), lambda p: str(fn(str(p))), custom=True)


def select(parsers: list[Parser], only: list[str] | None) -> list[Parser]:
    ps = [p for p in parsers if p.available]
    if only:
        wanted = {o.lower() for o in only}
        ps = [p for p in ps if p.name.lower() in wanted or p.custom]
    return ps


def ext_fmt(path: Path) -> str | None:
    return {".pdf": "pdf", ".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx", ".html": "html", ".htm": "html",
            ".eml": "eml"}.get(path.suffix.lower())


__all__ = ["Parser", "builtin_parsers", "command_parser", "python_parser", "select", "ext_fmt"]
