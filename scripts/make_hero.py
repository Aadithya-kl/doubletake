"""Build assets/hero.png and assets/social-preview.png from a real forged document.

    python scripts/make_hero.py
"""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from doubletake.forge import by_id
from doubletake.parsers import _pypdf

ROOT = Path(__file__).resolve().parents[1]
CANARY = "DTKHX7RC4MA"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BG, INK, MUTED, RED, PANEL, TERM = "#0d1117", "#e6edf3", "#8b949e", "#ff6b6b", "#161b22", "#010409"


def f(path, size):
    return ImageFont.truetype(path, size)


def page_image(td: Path) -> Image.Image:
    pdf = by_id()["pdf.white_text"].build(td / "invoice", CANARY)
    subprocess.run(["pdftoppm", "-r", "110", "-png", "-singlefile", str(pdf), str(td / "page")], check=True)
    img = Image.open(td / "page.png").convert("RGB")
    return img.crop((0, 0, img.width, int(img.height * 0.42))), pdf


def hero() -> Image.Image:
    with tempfile.TemporaryDirectory() as tds:
        td = Path(tds)
        page, pdf = page_image(td)
        text = _pypdf(pdf)
    W, H = 1600, 860
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((60, 40), "DoubleTake", font=f(BOLD, 44), fill=INK)
    d.text((60, 100), "The same PDF. What the human sees vs. what the LLM reads.", font=f(FONT, 26), fill=MUTED)

    # left: rendered page
    pw = 700
    page = page.resize((pw, int(page.height * pw / page.width)))
    d.text((60, 170), "Rendered page (what a person sees)", font=f(BOLD, 22), fill=INK)
    d.rounded_rectangle((52, 207, 60 + pw + 8, 215 + page.height + 8), 10, fill="#30363d")
    im.paste(page, (60, 215))

    # right: parser output
    x0 = 60 + pw + 60
    d.text((x0, 170), "pypdf.extract_text() (what the model gets)", font=f(BOLD, 22), fill=INK)
    d.rounded_rectangle((x0 - 8, 207, W - 52, 215 + page.height + 8), 10, fill=TERM)
    y, mono = 232, f(MONO, 19)
    for line in text.splitlines():
        hidden = CANARY in line or "pre-approved" in line or "note." in line
        for chunk in textwrap.wrap(line, 56) or [""]:
            d.text((x0 + 14, y), chunk, font=mono, fill=RED if hidden else "#c9d1d9")
            y += 30
    d.text((x0 + 14, y + 10), "^ white text: invisible on the page, read by the model", font=f(FONT, 18), fill=RED)

    bottom = 215 + page.height + 50
    d.text((60, bottom), "37 hiding techniques · PDF DOCX XLSX PPTX HTML EML · 118 leaks across 20 common parsers · "
           "test your own pipeline", font=f(FONT, 22), fill=MUTED)
    return im.crop((0, 0, W, bottom + 60))


def social(h: Image.Image) -> Image.Image:
    W, H = 1280, 640
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((70, 70), "DoubleTake", font=f(BOLD, 84), fill=INK)
    d.text((70, 180), "Find where your document pipeline shows the LLM", font=f(FONT, 36), fill=INK)
    d.text((70, 228), "something the human never saw.", font=f(FONT, 36), fill=INK)
    crop = h.crop((40, 160, 1600, h.height - 70))
    crop = crop.resize((1140, int(crop.height * 1140 / crop.width)))
    im.paste(crop, (70, 300))
    d.rectangle((0, H - 8, W, H), fill=RED)
    return im


if __name__ == "__main__":
    (ROOT / "assets").mkdir(exist_ok=True)
    h = hero()
    h.save(ROOT / "assets" / "hero.png", optimize=True)
    social(h).save(ROOT / "assets" / "social-preview.png", optimize=True)
    print("wrote assets/hero.png and assets/social-preview.png")
