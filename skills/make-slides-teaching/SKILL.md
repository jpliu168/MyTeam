---
name: make-slides
description: Making lecture decks (.pptx) for {{GROUP}} — structure, accessibility, speaker notes. Use for any lecture, tutorial or workshop slides.
---

# Making lecture slides for {{GROUP}}

Mechanics: real .pptx files with python-pptx (`pip install python-pptx
--user` if missing), saved to `{{STATE}}/deliverables/lectures/week-NN/`
with `outline.md` (one line per slide) for the instructor to approve first.

Structure that works for a 50–75 minute class:
1. Title + today's learning objectives (2–3, from the course plan).
2. Hook: a question, demo or real example.
3. 3–4 chunks of 10–15 min: concept → worked example → quick check
   (poll/question slide).
4. One in-class activity slide with clear steps and time.
5. Recap + what's due next (dates from the course plan) + resources.

Style: ≥24pt body text, high contrast, one idea per slide, real slide titles
(screen readers use them), alt text on every image, no text baked into
images, no information by color alone. Code in a monospace font, large.
Speaker notes on every slide: what to SAY and timing. Never invent data or
citations; cite figure sources on the slide.
