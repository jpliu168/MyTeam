# MyTeam

**A team of agents for a small business or a one-person company: one owner,
many roles.** Same core as MyLab (control room, task board, message bus,
standup, shared handbook and deliverables), with business roles instead of
research ones.

## Install & found your team

```bash
cd ~/agents/MyTeam && ./install.sh
myteam
```

First run asks what kind of team it is, then its name, then runs the hiring
loop. Five field presets — each brings its own roles, shared skills, profile
form, handbook starter, and how agents address you:

| Preset | You are | Roles on offer |
|---|---|---|
| Small business / company | owner | operations manager, executive assistant, bookkeeper, tax prep, customer support, sales, marketing, copywriter, market researcher, contracts & compliance, HR, data analyst, reviewer |
| University research lab | PI | chief of staff, proposal writer, manuscript writer, lit scout, HPC runner, data analyst, slides maker, reviewer, grants admin, outreach |
| Teaching / a course | instructor | course manager, course designer, lecture & slides maker, assignment & quiz writer, grading assistant, student Q&A, lab & code developer, accessibility checker, LMS admin, reviewer |
| Nonprofit / community | director | operations manager, program coordinator, grant writer, donor relations, volunteer coordinator, events, communications, board secretary, bookkeeper, reviewer |
| Freelancer / creator | owner | studio manager, client manager, proposals & invoices, content producer, social & newsletter, portfolio & web, scheduler, bookkeeper & tax, reviewer |

Every preset also has a generalist and custom roles, and you can hire a role
from any other preset. Change the preset later in Setup; existing members
keep their roles.

## Run the team

Everything works like MyLab, with `myteam` in place of `mylab`:

```bash
myteam                       # the control room (sidebar, feed, input line)
myteam up | start sam | open sam
myteam assign tina "organize Q3 receipts into deliverables/books/"
myteam standup | tasks | done 3
myteam hire | edit sam | retire sam
```

In the control room: `sam: <msg>`, `@all <msg>`, `assign`, `tasks`,
`standup`, `watch on|off`, `setup`, `help`, `quit`. Your prompt is `you>`.

## The web control room

```bash
myteam-web            # starts a local web server and opens your browser
myteam-web url        # print the link of the running server
myteam-web stop       # shut it down (the team keeps working)
```

Same control room in a browser: members with live status, the briefing,
the feed with replies, the same input box (`sam: …`, `@all …`, `assign …`),
a Tasks tab with ✓ done buttons, and a Files tab to read deliverables/ and
handbook/. Click any member to watch their terminal live and answer their
prompts (e.g. the first-run trust question) without leaving the browser.
Local only: it listens on 127.0.0.1 and every request needs the per-run key
in the link it prints. Runs alongside the terminal `myteam` — use either.

## Shared knowledge

- `~/myteam/handbook/` — about, offer, pricing, policies, voice, FAQ,
  approved replies, chart of accounts. Members quote it instead of inventing
  prices or policies.
- `~/myteam/deliverables/` — books/, tax/, support/, sales/, marketing/,
  copy/, research/, compliance/ … all finished work.
- `MyTeam/skills/` — common skills rendered into every member: team-collab,
  house-style (business voice), customer-replies, money-records, make-slides.

## Hard rules baked into every member

Agents draft and prepare; **the owner sends, signs, pays and files.** No
moving money, no logging in to bank/tax/payment portals, no answering
password/2FA prompts, no posting publicly, no prices/discounts/refunds/
promises that aren't in the handbook, no fake reviews. Tax prep and
contracts are organizing help, not tax or legal advice — judgment calls are
flagged for the CPA or attorney.

## MyTeam and MyLab side by side

Separate command (`myteam`), state (`~/myteam/`), tmux sessions
(`myteam-*`) and env vars (`MYTEAM_*`) — both can run at once. Note that
`tmux kill-server` stops both; use `myteam kill <m>` to stop one member.
