---
name: fetch-paper
description: Getting the full text of a paper from a DOI, arXiv ID, title, or URL — legally and verifiably. Use whenever a task needs a paper's actual content (related work, citation checks, reproduction).
---

# Fetching papers

Goal: the real full text, provenance recorded, never a summary hallucinated
from a title.

Order of attack (first verified hit wins):
1. Publisher page — many are open access.
2. arXiv / preprint servers (label the result PREPRINT — it may differ from
   the published version).
3. OpenAlex / Unpaywall / Crossref for a legal OA copy.
4. Europe PMC / PubMed Central for biomedical.
5. If the `fetch-paper` command-line tool is installed (`which fetch-paper`), use
   it — it automates exactly this ladder and verifies full text.

Rules:
- Verify you actually got the paper (title + authors match; >1 page of body).
- Save the PDF and a `source.txt` (where, when, which version) next to it in
  `{{STATE}}/deliverables/lit/`.
- Paywalled and no legal copy? Say so and give the PI the citation — never
  pirate, never fake familiarity with a paper you could not read.
- When citing later: page/section numbers come from the copy you saved, not
  from memory.
