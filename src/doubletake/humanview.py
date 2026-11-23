"""'What the human sees': render the document to pixels, then OCR it.

PDF  -> pdftoppm -> tesseract
DOCX / XLSX / PPTX -> LibreOffice -> PDF -> (same)
HTML -> headless Chrome (fallback wkhtmltopdf) -> PDF -> (same)
EML  -> the part a mail client displays (HTML preferred) plus visible headers -> HTML route
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

DPI = 200


class RenderError(RuntimeError):
    pass


def _eml_as_displayed(path: Path) -> str:
    import email
    import html as h
    from email import policy

    m = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    head = "".join(f"<div>{k}: {h.escape(str(m[k] or ''))}</div>" for k in ("From", "To", "Subject"))
    body = m.get_body(preferencelist=("html", "plain"))
    content = "" if body is None else body.get_content()
    if body is not None and body.get_content_type() == "text/plain":
        content = f"<pre>{h.escape(content)}</pre>"
    return f"<html><head><meta charset='utf-8'></head><body>{head}<hr>{content}</body></html>"


def _to_pdf(path: Path, td: Path) -> Path:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return path
    if ext == ".eml":
        html = td / (path.stem + ".html")
        html.write_text(_eml_as_displayed(path), encoding="utf-8")
        return _to_pdf(html, td)
    if ext in (".docx", ".xlsx", ".pptx"):
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(td), str(path)],
                       capture_output=True, timeout=180)
        out = td / (path.stem + ".pdf")
    elif ext in (".html", ".htm"):
        out = td / (path.stem + ".pdf")
        chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
        if chrome:
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                            f"--user-data-dir={td / 'chrome-profile'}",
                            f"--print-to-pdf={out}", path.resolve().as_uri()], capture_output=True, timeout=120)
        elif shutil.which("wkhtmltopdf"):
            subprocess.run(["wkhtmltopdf", "-q", str(path), str(out)], capture_output=True, timeout=120)
    else:
        raise RenderError(f"unsupported format: {ext}")
    if not out.exists():
        raise RenderError(f"could not render {path.name} to PDF")
    return out


def render_and_ocr(path: Path, dpi: int = DPI) -> str:
    import pytesseract
    from PIL import Image

    with tempfile.TemporaryDirectory() as tds:
        td = Path(tds)
        pdf = _to_pdf(path, td)
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(td / "page")],
                       capture_output=True, timeout=180, check=True)
        pages = sorted(td.glob("page*.png"))
        if not pages:
            raise RenderError("renderer produced no pages")
        return "\n".join(pytesseract.image_to_string(Image.open(pg)) for pg in pages)
