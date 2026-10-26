---
name: team-data
description: How {{GROUP}} keeps lists of people, organizations and things (experts, contacts, vendors, customers, leads, grants ...) as searchable, updatable tables with `myteam db`. Use whenever a job collects, looks up, updates or exports a list — instead of writing loose CSV files.
---

# Team tables: `myteam db`

Lists the team builds up (experts found on the web, contacts, vendors,
customers, leads, funding calls ...) live in ONE shared database,
`{{STATE}}/data/team.db`, not in scattered CSV files. It is searchable,
updatable and remembers where every fact came from.

## Before you search the web, search the table

```bash
myteam db                                          # which tables exist
myteam db search experts "reinforcement learning robotics"
myteam db search experts "LLM" --where country=US -n 30
myteam db show experts "Jane Doe"                  # one record + sources + history
```

Only go to the web for what is missing or stale.

## Saving what you found

Write rows to a CSV or JSON file in your workspace, then add them:

```bash
myteam db new experts "AI experts for the advisory board"   # first time only
myteam db add experts --from found.csv
myteam db add experts name="Jane Doe" affiliation=MIT expertise="RL; robotics" \
    openalex_id=A5023888391 source=https://openalex.org/A5023888391
```

- **Adding again updates; it never duplicates.** A record is matched by its
  IDs (openalex_id, orcid, email, homepage, website, linkedin, url), or else
  by name + organization. Empty values never erase existing data.
- **Always include a stable ID when you can.** For researchers, look up the
  OpenAlex author ID (`openalex_id`) or ORCID. For companies, use the website.
- **Always include `source`.** Put the URL where you found the fact in a
  `source` column (separate several with `;`). Don't add facts you can't source.
- Use plain, lowercase column names and reuse the ones the table already has
  (`myteam db search <table> --csv | head -1` shows them). Put lists in one
  cell, separated by `;`.
- Read the add summary. `! possible duplicate` or `kept existing ...` means
  two records may be the same person. Check, then
  `myteam db set <table> <id> status=duplicate` on the extra one, or leave
  both if they are different people.

## Keeping it current

```bash
myteam db stale experts --days 180                 # who needs re-checking
myteam db set experts <id> affiliation="Stanford" source=https://...
myteam db set experts <id> status=moved            # moved | retired | duplicate | active
myteam db verify experts <id> --source https://... # checked, still correct
myteam db history experts                          # who changed what
```

## Handing it over

```bash
myteam db export experts          # → {{STATE}}/deliverables/data/experts.csv (opens in Excel)
myteam db search experts "climate" --csv > my-shortlist.csv
myteam db sql "SELECT status, COUNT(*) FROM records WHERE tbl='experts' GROUP BY status"
```

## Rules

- Only the {{BOSS}} removes records. If something should go, set
  `status=duplicate` or `retired`, or file
  `myteam request other "remove <id> from <table>: why"`.
- Personal contact details: store only what is public or what the {{BOSS}} gave you.
- Tell the manager the table and how many rows changed, for example:
  `myteam report "experts: 42 new, 7 updated — export in deliverables/data/experts.csv"`.
