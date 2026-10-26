---
name: expert-database
description: How {{GROUP}} builds and maintains the on-campus `experts` table (who does what research) and matches people to funding calls or media requests. Use whenever a job looks up, adds, updates or recommends campus researchers.
---

# The campus expert database

The `experts` table (`myteam db`) is the office's map of who does what.
Treat it as a shared, long-lived asset: accurate, sourced, current.

## Public, professional information only

Record what a person publishes about their professional work: name, title,
department, college, public directory email, research areas, publications,
awards, centers, profile pages. Never record home addresses, personal phone
numbers, salaries, demographics, health, immigration or anything private —
even if you find it.

## Sources (in this order)

1. The university directory and department/faculty profile pages
2. OpenAlex (`api.openalex.org/authors?filter=affiliations.institution.id:…`) — topics, works, `openalex_id`
3. ORCID public records
4. NSF award search and NIH RePORTER — current/recent awards (title, sponsor, amount, end date)
5. Lab / personal research pages, Google Scholar profile pages if reachable

## Columns

`name`, `title`, `department`, `college`, `email`, `areas`, `keywords`,
`centers`, `recent_awards`, `openalex_id`, `orcid`, `homepage`,
`media_ready` (yes if they've done press), `status` (active | moved | retired | duplicate),
`last_verified` (YYYY-MM-DD), `source` (URLs, `;`-separated).
Use `openalex_id` / `orcid` / `homepage` as identity whenever possible.

```bash
myteam db new experts "on-campus research experts"      # first time
myteam db add experts --from dept-chemistry.csv          # re-adding updates
myteam db search experts "machine learning materials"
myteam db stale experts --days 180
myteam db set experts <id> status=moved source=https://...
myteam db verify experts <id> --source https://...
```

## Building it

Go department by department; keep a progress note in
`deliverables/experts/coverage.md` (which units are done, when, gaps).
Check name variants and duplicates after each batch.

## Matching

For "who fits this call / this media question": search the table, then
rank 3–8 people. For each give one line of evidence (a paper, award or
center, with link) and note conflicts (already on a competing bid,
on leave). The {{BOSS}} decides whom to contact; you never contact faculty.
