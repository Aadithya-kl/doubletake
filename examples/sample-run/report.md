# DoubleTake probe report

Canary: `DTKKAMVHAKN` · techniques: 37 (37 confirmed hidden on the rendered page) · parsers: 20

**118 split-view leak(s)**: a parser handed the model text that the rendered page does not show.

## Parser exposure

| Parser | Leaked / tested split-view techniques |
|---|---|
| markitdown | 28 / 34 |
| pypdf+metadata | 8 / 9 |
| raw-html | 8 / 8 |
| pdfminer.six | 7 / 9 |
| pdfplumber | 7 / 9 |
| pypdf | 7 / 9 |
| pdftotext | 6 / 9 |
| python-pptx+notes | 6 / 6 |
| bs4 (strip script/style) | 5 / 8 |
| bs4.get_text | 5 / 8 |
| openpyxl (all cells) | 5 / 6 |
| python-docx+metadata | 5 / 5 |
| python-pptx | 5 / 6 |
| libreoffice-txt | 4 / 5 |
| python-docx | 4 / 5 |
| email (all parts+headers) | 3 / 3 |
| email (plain preferred) | 2 / 3 |
| email (html preferred) | 1 / 3 |
| openpyxl (comments) | 1 / 6 |
| openpyxl (visible only) | 1 / 6 |

## PDF

| Technique | Hidden on page? | pypdf | pypdf+metadata | pdfplumber | pdfminer.six | pdftotext | markitdown |
|---|---|---|---|---|---|---|---|
| `pdf.white_text` White-on-white text | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `pdf.tiny_font` Microscopic font | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `pdf.render_mode_3` Invisible render mode | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `pdf.off_page` Off-page coordinates | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | · | **LEAK** |
| `pdf.covered` Covered by shape | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `pdf.clipped` Clipped away | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `pdf.alpha_zero` Zero opacity | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `pdf.metadata` Document metadata | yes | · | **LEAK** | · | · | · | · |
| `pdf.annotation` Zero-size annotation | yes | · | · | · | · | · | · |

## DOCX

| Technique | Hidden on page? | markitdown | python-docx | python-docx+metadata | libreoffice-txt |
|---|---|---|---|---|---|
| `docx.hidden_run` Hidden run (w:vanish) | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `docx.white_text` White text | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `docx.tiny_font` 1pt font | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `docx.core_properties` Core properties | yes | · | · | **LEAK** | · |
| `docx.unicode_tags` Unicode tag smuggling | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |

## XLSX

| Technique | Hidden on page? | markitdown | openpyxl (all cells) | openpyxl (visible only) | openpyxl (comments) |
|---|---|---|---|---|---|
| `xlsx.hidden_sheet` Hidden worksheet | yes | **LEAK** | **LEAK** | · | · |
| `xlsx.very_hidden_sheet` Very hidden worksheet | yes | **LEAK** | **LEAK** | · | · |
| `xlsx.hidden_row` Hidden row | yes | **LEAK** | **LEAK** | · | · |
| `xlsx.hidden_column` Hidden column | yes | **LEAK** | **LEAK** | · | · |
| `xlsx.white_text` White text | yes | **LEAK** | **LEAK** | **LEAK** | · |
| `xlsx.cell_comment` Cell comment | yes | · | · | · | **LEAK** |

## PPTX

| Technique | Hidden on page? | markitdown | python-pptx | python-pptx+notes |
|---|---|---|---|---|
| `pptx.speaker_notes` Speaker notes | yes | **LEAK** | · | **LEAK** |
| `pptx.off_slide` Off-slide shape | yes | **LEAK** | **LEAK** | **LEAK** |
| `pptx.white_text` White text | yes | **LEAK** | **LEAK** | **LEAK** |
| `pptx.tiny_font` 1pt font | yes | **LEAK** | **LEAK** | **LEAK** |
| `pptx.hidden_shape` Hidden shape | yes | **LEAK** | **LEAK** | **LEAK** |
| `pptx.behind_shape` Covered by shape | yes | **LEAK** | **LEAK** | **LEAK** |

## HTML

| Technique | Hidden on page? | markitdown | bs4.get_text | bs4 (strip script/style) | raw-html |
|---|---|---|---|---|---|
| `html.display_none` display:none | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `html.font_size_zero` font-size:0 | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `html.color_match` Colour-matched text | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `html.offscreen` Off-screen positioning | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |
| `html.comment` HTML comment | yes | · | · | · | **LEAK** |
| `html.img_alt` Image alt text | yes | **LEAK** | · | · | **LEAK** |
| `html.aria_label` aria-label attribute | yes | · | · | · | **LEAK** |
| `html.unicode_tags` Unicode tag smuggling | yes | **LEAK** | **LEAK** | **LEAK** | **LEAK** |

## EML

| Technique | Hidden on page? | email (plain preferred) | email (html preferred) | email (all parts+headers) |
|---|---|---|---|---|
| `eml.plain_html_mismatch` text/plain vs text/html mismatch | yes | **LEAK** | · | **LEAK** |
| `eml.html_display_none` Hidden HTML in email | yes | **LEAK** | **LEAK** | **LEAK** |
| `eml.custom_header` Custom X- header | yes | · | · | **LEAK** |

---

**LEAK**: the parser output contains the canary while OCR of the rendered page does not.  
`(visible)`: the technique did not hide the payload in this renderer, so it is not counted.  
`INFLUENCED` / `resisted`: result of the optional `--llm` check.  
The forged documents are kept next to this report, so you can open each one yourself.
