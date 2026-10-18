---
name: make-slides
description: Making presentation decks (.pptx) for {{GROUP}} — structure, style, and mechanics. Use for any talk, defense, seminar, or pitch deck request.
---

# Making slides for {{GROUP}}

Mechanics: build real .pptx files with python-pptx (`pip install
python-pptx --user` if missing). Output to
`{{STATE}}/deliverables/<talk-name>/` as `<talk-name>.pptx` plus
`outline.md` (one line per slide) so the PI can approve the story in 60
seconds before opening PowerPoint.

Structure that works for research talks:
1. Title (talk title, speaker, venue, date — from the handbook).
2. The problem in ONE slide, concrete.
3. "What we did" overview figure.
4. 3–5 result slides: one idea each, figure-dominant, caption = finding.
5. Limitations, honestly.
6. Take-home + acknowledgments (funders from the handbook — never omit).

Style: big text (≥20pt), dark-on-light, no paragraph on a slide, no clip
art. Figures come from deliverables/ (ask data-analyst or hpc-runner over the
bus if one is missing — do not fake a figure). Every slide gets speaker
notes: what to SAY, not what is shown. 1 slide ≈ 1 minute of talk.
