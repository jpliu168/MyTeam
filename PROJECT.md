# MyTeam — project state & decisions (portable source of truth)

- **Owner:** Paul Liu (jpliu@ncsu.edu).
- **What:** MyLab forked for small businesses / one-person companies. Same
  core (tmux sessions, bus, board, daemon, control-room TUI, skills
  renderer); business roles, vocabulary and skills.
- **Folder:** `/Users/jpliu/agents/MyTeam/` (command `myteam`), state in
  `~/myteam/`, tmux prefix `myteam-`, env `MYTEAM_*`. MyLab untouched.
- **Created:** 2026-10-16 as a separate copy (Paul's choice) — core fixes
  must be applied to both MyLab and MyTeam.

## Differences from MyLab
- Roles: operations-manager, executive-assistant, bookkeeper, tax-prep,
  customer-support, sales, marketing, copywriter, market-researcher,
  contracts-compliance, hr, data-analyst, reviewer, generalist.
- Skills: team-collab, house-style (business voice), customer-replies,
  money-records (replaces fetch-paper), make-slides (business decks).
- Vocabulary: PI → owner (prompt `you>`, bus sender "owner"), lab → team,
  实验室 → 团队; handbook seeded with business files (pricing, policies,
  voice, FAQ, approved replies, chart of accounts).
- Hard rule: agents draft/prepare; owner sends, signs, pays, files.
- Fixes applied here first (not yet in MyLab): standup skips dotfiles
  (.DS_Store); sidebar width fits the shortcut text; member names up to 12
  chars in the sidebar; `office` banner uses the team name, not "Liu Lab".

## Briefing (added 2026-10-16)
- Pinned panel at the top of the control-room feed: one line per member —
  status, role, what they're doing, open tasks, age. `brief` prints the full
  briefing into the feed; `brief on|off` toggles the panel; `myteam brief`
  from any shell.
- Source order (lib/myteam/brief.py): member's own note (`myteam now "..."`,
  members/<name>/NOW.json, fresh < 6h) → Claude Code's tmux pane title →
  newest open task → last bus message. team-collab skill tells members to
  keep `myteam now` current.
- Also fixed: title bar/feed now measure CJK width (stray clock digit gone).

## Web control room (added 2026-10-16)
- `myteam-web` (bin/myteam-web → lib/myteam/web.py, page in lib/myteam/webui/index.html).
  stdlib ThreadingHTTPServer on 127.0.0.1 (port 8765+), per-run token
  (?t= → HttpOnly SameSite cookie), Host-header check, files limited to
  deliverables/ + handbook/. web.json in ~/myteam/ makes a second launch reopen
  the same server. Background Hub thread mirrors the TUI poller.
- Page: members sidebar, briefing, feed + composer (same command language),
  Tasks/Files tabs, member terminal drawer (live tail + owner keystrokes:
  Send+Enter, Enter, ↑↓, Esc; Start/Stop), EN/中文 toggle, light/dark, phone layout.
- Replies (TUI + web) now start after the injected "[myteam …]" line.

## Setup in the web + company profile (added 2026-10-16)
- ⚙ Setup drawer: team name, language, hire/edit/retire (archive only), re-render
  skills. Chinese-only names get an internal key member-N; display stays as typed.
- Company profile (lib/myteam/profile.py, 16 fields: business, industry, entity,
  location, products, customers, pricing, voice, goals, owner's rules …) in
  config.json "profile" → rendered into every member as the `company-profile`
  skill + handbook/company-profile.md. Also TUI setup option 6.

## Field presets (added 2026-10-17)
- lib/myteam/packs.py: business, research, teaching, nonprofit, freelance —
  boss word ({{BOSS}}: owner/PI/instructor/director), unit ({{UNIT}}), skill
  map (render-name → skills/<dir>), handbook starter. cfg["pack"], default business.
- roles.py: BY_PACK libraries + ZH labels; by_id() prefers the team's preset.
- profile.py: per-preset fields; skill/handbook name per preset
  (company-/lab-/course-/organization-/practice-profile).
- skills.sync renders only the preset's skills, keeps a manifest
  (.claude/skills/.myteam-generated.json) and removes stale generated ones.
- New skills: house-style-{research,teaching,nonprofit}, fetch-paper,
  make-slides-{research,teaching}, student-privacy, course-materials, donor-care.
- First-run wizard asks the preset; TUI setup 7; web Setup "Field preset"
  select; hire form groups roles by preset (★ = current).

## Open / next
- Port the three fixes above back to MyLab.
- Customer support can only draft; a real inbox/helpdesk connection would be
  a later, owner-approved step.
- Same open items as MyLab: status regexes, no per-agent resume.
