# MyTeam

**You talk to one manager; the manager runs a team of specialist agents that
know your organization and get better at its work every week.** For a small
business, a one-person company, a research lab, a university office, a
dean or department head, a graduate student, a course, a nonprofit, or a
freelance practice.
See [DESIGN.md](DESIGN.md) for the why and the rules.

## Install & found your team

Requires macOS or Linux, Python 3, tmux, and [Claude Code](https://claude.com/claude-code)
(Codex and Gemini CLI are optional).

> **Windows users:** MyTeam does **not** run from Command Prompt (cmd) or
> PowerShell — it needs tmux and a Linux terminal. Install it inside **WSL**
> (Windows Subsystem for Linux, built into Windows 10/11) using the
> [Windows steps](#windows-wsl) below. It then works exactly as on a Mac.

### macOS / Linux

```bash
git clone https://github.com/jpliu168/MyTeam.git
cd MyTeam && bash install.sh
myteam
```

On a Mac, install tmux first if you don't have it: `brew install tmux`.

### Windows (WSL)

One-time setup, about 10 minutes.

1. **Install WSL.** Open **PowerShell as Administrator** (Start menu → type
   "PowerShell" → right-click → *Run as administrator*) and run:

   ```powershell
   wsl --install
   ```

   Restart Windows when it finishes. Ubuntu opens and asks you to pick a
   Linux username and password (it's separate from your Windows login).

2. **Open "Ubuntu"** from the Start menu. Run every command from here on in
   this Ubuntu window — not in cmd or PowerShell.

3. **Install the tools, Claude Code, and MyTeam:**

   ```bash
   sudo apt update && sudo apt install -y git tmux python3
   curl -fsSL https://claude.ai/install.sh | bash
   claude            # sign in once, then type /exit
   git clone https://github.com/jpliu168/MyTeam.git
   cd MyTeam && bash install.sh
   ```

   If the installer says `~/.local/bin` is not on your PATH, run
   `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`.

4. **Start your team:** `myteam`

Good to know on Windows:

- **Always start MyTeam from the Ubuntu app.** Typing `myteam` in cmd or
  PowerShell won't work.
- **Web control room:** `myteam-web` works and opens in your normal Windows
  browser. If no browser appears, run `myteam-web url` and paste the link.
- **Your team's files** live in Linux at `~/myteam`. In File Explorer, open
  `\\wsl$\Ubuntu\home\<your-linux-username>\myteam`.
- **Windows folders** are visible to agents under `/mnt/c/` — e.g.
  `/mnt/c/Users/<you>/Documents`.
- **Update later:** `cd ~/MyTeam && git pull`.

First run asks what kind of team it is, then its name, then runs the hiring
loop. Eight field presets — each brings its own roles, shared skills, profile
form, handbook starter, and how agents address you:

| Preset | You are | Roles on offer |
|---|---|---|
| Small business / company | owner | operations manager, executive assistant, bookkeeper, tax prep, customer support, sales, marketing, copywriter, market researcher, contracts & compliance, HR, data analyst, reviewer |
| University research lab | PI | chief of staff, proposal writer, manuscript writer, lit scout, HPC runner, data analyst, slides maker, reviewer, grants admin, outreach, news watcher |
| University research office | director | chief of staff, funding scout, expert-database curator, proposal coordinator, development writer, news & social media, events & training, research analytics, compliance & awards, reviewer, news watcher |
| Academic leadership (dean / dept head) | dean/head | chief of staff, faculty affairs, curriculum & scheduling, student programs, budget & resources, assessment & accreditation, unit analytics, governance & committees, advancement & alumni, communications, reviewer, news watcher |
| Graduate student (MS / PhD) | grad student | manager, research assistant, literature reader, coursework & study coach, dissertation/thesis writer, manuscript writer, data & figures, lab & group life, degree milestones & paperwork, fellowships & career, slides & posters, TA helper, reviewer, news watcher |
| Teaching / a course | instructor | course manager, course designer, lecture & slides maker, assignment & quiz writer, grading assistant, student Q&A, lab & code developer, accessibility checker, LMS admin, reviewer |
| Nonprofit / community | director | operations manager, program coordinator, grant writer, donor relations, volunteer coordinator, events, communications, board secretary, bookkeeper, reviewer |
| Freelancer / creator | owner | studio manager, client manager, proposals & invoices, content producer, social & newsletter, portfolio & web, scheduler, bookkeeper & tax, reviewer |

The **news watcher** collects public news about your team, lab or group (LinkedIn posts that
show up in search, university news, X/Bluesky, award announcements, alerts you forward) into a
`news` table and a weekly digest. It never logs in to LinkedIn or scrapes it — forward
LinkedIn notification emails or paste posts for anything behind the login.

Every preset also has a generalist and custom roles, and you can hire a role
from any other preset. Change the preset later in Setup; existing members
keep their roles.

## Run the team

Everything works like MyLab, with `myteam` in place of `mylab`:

```bash
myteam                       # the control room (sidebar, feed, input line)
myteam up | start alex | open alex
myteam assign tina "organize Q3 receipts into deliverables/books/"
myteam standup | tasks | done 3
myteam hire | edit alex | retire alex
```

In the control room: `alex: <msg>`, `@all <msg>`, `assign`, `tasks`,
`standup`, `watch on|off`, `setup`, `help`, `quit`. Your prompt is `you>`.

## The web control room

```bash
myteam-web            # starts a local web server and opens your browser
myteam-web url        # print the link of the running server
myteam-web stop       # shut it down (the team keeps working)
```

Same control room in a browser: members with live status, the briefing,
the feed with replies, the same input box (`alex: …`, `@all …`, `assign …`),
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

## Profiles — more than one team

Run 2–3 separate teams side by side, e.g. a lab for your PI work and a
research office for your admin work:

```bash
myteam use research-admin     # creates it (setup asks the preset) or switches to it
myteam use research-pi
myteam list                   # all profiles, * = active, what's running
myteam -p research-admin inbox   # one command against another profile
```

`~/myteam` stays the `default` profile; new ones live in `~/myteam/profiles/<name>/`.
The **research-admin** preset gives a chief of staff plus a funding scout,
campus expert-database curator, proposal development coordinator,
development writer, news & social media manager, events & training,
research analytics, compliance & award tracking, and a reviewer.

The **academic-admin** preset (dean or department head) gives a chief of
staff plus faculty affairs (searches, P&T, reviews), curriculum & course
scheduling, student programs, budget & resources, assessment &
accreditation, unit analytics, governance & committees, advancement &
alumni, communications, and a reviewer. Personnel and student records follow
the `confidential-records` skill. `myteam use dean` or `myteam use dept-head`
picks this preset automatically.

The **graduate** preset (MS or PhD student) gives you a manager who keeps
your degree plan, weekly plan and advisor-meeting updates, plus agents for
each part of grad school: a research assistant (methods, experiments, code,
run log), a literature reader (`papers` table, BibTeX, reading notes,
weekly digests), a coursework & study coach, a dissertation/thesis writer,
a manuscript writer, data & figures, lab & group life (lab meetings,
journal club, protocols), degree milestones & paperwork, fellowships &
career, slides & posters, a TA helper, a reviewer and a news watcher.
The `academic-integrity` skill keeps it honest: the coach teaches and quizzes
but never writes graded work, every number and citation traces to a real
source, and agents log where they helped so you can disclose AI use. Students
can run one profile per part of their life, e.g.:

```bash
myteam use phd          # research, thesis, papers, lab
myteam use classes      # set up with the graduate preset for coursework
```

Names with `grad`, `phd`, `student`, `thesis`, `dissertation` or `masters`
pick the graduate preset automatically.

## License

MyTeam is released under the [MIT License](LICENSE) — © 2026 Paul Liu.
You may use, copy, modify and share it, including commercially, as long as
the copyright and license notice stay with it. It comes with no warranty.
