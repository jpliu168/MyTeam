---
name: make-slides
description: Making presentation decks (.pptx) for {{GROUP}} — pitch decks, sales presentations, investor/lender updates, workshops. Use for any slide deck request.
---

# Making slides for {{GROUP}}

Mechanics: build real .pptx files with python-pptx (`pip install
python-pptx --user` if missing). Output to
`{{STATE}}/deliverables/<deck-name>/` as `<deck-name>.pptx` plus
`outline.md` (one line per slide) so the {{BOSS}} can approve the story in 60
seconds before opening PowerPoint.

Structures that work:
- Sales/pitch: customer's problem → our offer → how it works → proof (real
  results only) → pricing/options (from handbook/pricing.md) → next step.
- Lender/investor update: snapshot numbers → what changed → plan → the ask.
- Workshop/talk: one idea per slide, examples over theory, a take-home slide.

Style: big text (≥20pt), the brand colors/logo from the handbook if present,
no paragraph on a slide, no clip art. Numbers and charts come from
deliverables/ (ask data-analyst or bookkeeper over the bus if one is missing —
never fake a figure, logo, or customer quote). Every slide gets speaker
notes: what to SAY, not what is shown.
