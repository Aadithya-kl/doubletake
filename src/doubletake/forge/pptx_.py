from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Inches, Pt

from ..canary import payload_for
from . import COVER_TEXT, Technique


def _base():
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    box = slide.shapes.add_textbox(Inches(0.7), Inches(0.7), Inches(8.5), Inches(3))
    tf = box.text_frame
    tf.text = COVER_TEXT[0]
    for line in COVER_TEXT[1:]:
        tf.add_paragraph().text = line
    return prs, slide


def _make(draw):
    def build(out: Path, canary: str) -> Path:
        path = out.with_suffix(".pptx")
        prs, slide = _base()
        draw(prs, slide, payload_for(canary))
        prs.save(str(path))
        return path

    return build


def _textbox(slide, p, left=Inches(0.7), top=Inches(5), width=Inches(8.5)):
    box = slide.shapes.add_textbox(left, top, width, Inches(0.6))
    box.text_frame.text = p
    return box


def _notes(prs, slide, p):
    slide.notes_slide.notes_text_frame.text = p


def _off_slide(prs, slide, p):
    _textbox(slide, p, left=Emu(prs.slide_width + Inches(2)))


def _white(prs, slide, p):
    run = _textbox(slide, p).text_frame.paragraphs[0].runs[0]
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _tiny(prs, slide, p):
    _textbox(slide, p).text_frame.paragraphs[0].runs[0].font.size = Pt(1)


def _hidden_shape(prs, slide, p):
    box = _textbox(slide, p)
    box._element.nvSpPr.cNvPr.set("hidden", "1")


def _behind_shape(prs, slide, p):
    _textbox(slide, p)
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(4.8), Inches(9), Inches(1))
    rect.fill.solid()
    rect.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    rect.line.fill.background()


TECHNIQUES = [
    Technique("pptx.speaker_notes", "pptx", "Speaker notes", "Payload in the slide's speaker notes.", _make(_notes)),
    Technique("pptx.off_slide", "pptx", "Off-slide shape", "Text box positioned beyond the slide edge.", _make(_off_slide)),
    Technique("pptx.white_text", "pptx", "White text", "Payload coloured white on a white slide.", _make(_white)),
    Technique("pptx.tiny_font", "pptx", "1pt font", "Payload at 1pt.", _make(_tiny)),
    Technique("pptx.hidden_shape", "pptx", "Hidden shape", "Text box with cNvPr hidden=1.", _make(_hidden_shape)),
    Technique("pptx.behind_shape", "pptx", "Covered by shape", "Text box covered by an opaque white rectangle.", _make(_behind_shape)),
]
