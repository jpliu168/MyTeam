---
name: funding-search
description: How {{GROUP}} finds and tracks funding opportunities (federal agencies, foundations, industry) in the `opportunities` table. Use for any funding sweep, digest, deadline check or "is there money for X" question.
---

# Finding funding opportunities

## Where to look (official sources first)

| sponsor | where |
|---|---|
| all federal | grants.gov (search + XML extract), SAM.gov Assistance Listings |
| NSF | nsf.gov/funding (program pages, "Dear Colleague Letters"), research.gov |
| NIH | grants.nih.gov/funding/searchguide (NIH Guide: NOFOs, NOSIs) |
| DOE | science.osti.gov/grants/FOAs, energy.gov program offices, ARPA-E (arpa-e-foa.energy.gov) |
| DOD | grants.gov + sam.gov BAAs; DARPA, ONR, AFOSR, ARO, DTRA program pages |
| NASA | nspires.nasaprs.com (ROSES and solicitations) |
| USDA | nifa.usda.gov funding opportunities |
| NOAA, EPA, NEH, NEA, IMLS, ED | each agency's funding page + grants.gov |
| foundations | the foundation's own site (Sloan, Moore, Keck, Simons, Gates, Packard, Research Corp …) |
| industry | company research-program pages (faculty awards, sponsored research calls) |
| state | state agency / economic development grant pages |

Use the priorities in the office profile and `{{STATE}}/handbook/sponsors.md`
to decide what to sweep. If the {{BOSS}} has a subscription database (e.g.
Pivot-RP) they can export it to you; you don't log in to anything.

## Search the table before the web

```bash
myteam db search opportunities "climate resilience"
myteam db stale opportunities --days 14
```

## What to record (one row per call)

`myteam db new opportunities "funding calls we track"` (first time), then add rows:

- `title`, `sponsor`, `program`, `number` (solicitation/NOFO #), `url` (official page)
- `loi_due`, `preproposal_due`, `full_due` — YYYY-MM-DD, as written by the sponsor (note the time zone)
- `award_size`, `num_awards`, `duration`
- `limited` (yes/no) and `limit` (e.g. "2 per institution")
- `eligibility`, `keywords`, `fit` (which priorities / units), `status` (open | forecast | closed | cancelled)
- `source` — the page where you read each fact

Use `number` or `url` as the identity so re-adding updates instead of
duplicating. Read the full solicitation: never record a deadline or dollar
figure you did not see on the sponsor's own page; if a page was unreachable,
say so.

## The weekly digest

`deliverables/funding/<YYYY-MM-DD>-digest.md`:

1. **Limited submissions** (internal competition needed) — first.
2. New calls, by deadline, one line each: sponsor · program · due · size · link.
3. Changed or cancelled calls.
4. "Who on campus fits" — ask the expert curator (or search the `experts`
   table) and name 2–5 people per major call, with the evidence.

Export for the {{BOSS}}: `myteam db export opportunities`.
