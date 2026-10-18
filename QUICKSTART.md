# MyTeam — Quickstart: your first day as owner of an agent team

Demo roster: **sam** (operations-manager), **bea** (bookkeeper),
**cara** (customer-support). Adjust to yours (`myteam roster`).

## 0. Fill the handbook (10 minutes — the biggest win)

```bash
open ~/myteam/handbook/
```

Add even short .md files: `about.md`, `pricing.md`, `policies.md` (refunds,
shipping, hours), `voice.md`, `faq.md`. Cara answers customers from these;
without them she can only say "I'll check with the owner".

## 1. Open the control room

```bash
myteam            # members do NOT auto-start
up                # start everyone + the mailman
```

## 2. Give work

```
assign bea put the September bank export (deliverables/books/inbox/sept.csv) into a ledger and summary
cara: here are three customer emails, draft replies: <paste>
@sam what's on the board, and what needs me today?
```

Drafts land in `~/myteam/deliverables/`. You review, then send/pay/post
yourself.

## 3. Members check each other

Ask sam to "have the reviewer check cara's drafts before I see them" — sam
runs `myteam ask <reviewer> ...` itself.

## 4. Daily rhythm

Morning `standup`; assign the day; `open <m>` wherever a ◐ needs you
(ctrl-b then d returns). Evening `standup` again.

| | |
|---|---|
| `myteam` | the control room |
| `up` · `start <m>` · `open <m>` | start all · start one · start + enter |
| `assign <m> <task>` · `tasks` · `done <id>` | the task board |
| `<m>: <msg>` · `@all <msg>` | talk |
| `setup` | hire / edit / retire, agent CLI, language |
| ctrl-b then d | leave a member's terminal — it keeps working |
