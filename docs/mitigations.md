# Fixing a leaking pipeline

No single setting closes every split view. Combine these, strongest first.

## 1. Extract what the human sees

The root cause is extracting from the document *model* instead of its *rendering*.

- **PDF / Office**: render pages and use OCR or a layout model that works on pixels, or at least compare
  extracted text against rendered OCR and drop what does not appear (this is what `doubletake scan` does).
- **HTML / email**: load the page in a real browser and take `document.body.innerText`. It respects CSS
  (`display:none`, `visibility`, zero sizes) much better than BeautifulSoup or Markdown converters.
  Off-screen and colour-matched text still need explicit checks.
- **Email**: use the same alternative the client displays (normally `text/html`) and flag messages whose
  `text/plain` and `text/html` parts disagree significantly.

## 2. Filter formatting that hides text

If you must use a text extractor, drop:

| Format | Drop |
|---|---|
| PDF | render mode 3/7; fill alpha 0; text outside the CropBox; font size < ~4pt; fill colour equal to the background; text under opaque later-painted shapes (needs a renderer) |
| DOCX | runs with `w:vanish`; runs below ~4pt; runs whose colour matches the shading |
| XLSX | sheets whose state is not `visible` (alert on `veryHidden`); hidden rows and columns; cells whose font colour matches the fill |
| PPTX | shapes with `hidden="1"`; shapes outside the slide; tiny or background-coloured runs |
| HTML | elements hidden by computed style; comments; attributes such as `alt` and `aria-label` unless labelled |

## 3. Strip invisible characters

Remove the Unicode tag block (U+E0000 to U+E007F) and audit other invisible code points (zero-width
characters, bidi controls, variation selectors) before text reaches the model.

```python
import re
INVISIBLE = re.compile(r"[\U000E0000-\U000E007F​-‏‪-‮⁠-⁤﻿]")
clean = INVISIBLE.sub("", text)
```

## 4. Label side channels instead of mixing them in

Metadata, speaker notes, comments, alt text and email headers are sometimes useful. Pass them in clearly
labelled, delimited sections ("Document metadata (untrusted): …"), never as body text.

## 5. Assume some hidden text gets through

Treat document content as data, not instructions:

- Keep instructions in the system prompt and document content in clearly delimited blocks.
- Do not let a document's content alone trigger consequential actions (approving payments, ranking
  candidates, sending email). Require structured, independently verified fields or a human decision based on
  the *rendered* document.
- Log the extracted text next to what was shown to the user, so you can investigate later.

## 6. Keep testing

Add `doubletake probe --fail-on-leak` to CI for your loader (see [ci.md](ci.md)). Parsers change between
versions, and so do their defaults.
