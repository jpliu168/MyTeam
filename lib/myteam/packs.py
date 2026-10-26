"""Field presets. A preset decides the default role library, which shared
skills every member gets, how agents address the human in charge, the
handbook starter, and the profile form. Chosen at first run; changeable in
Setup. Members hired from another preset keep working (roles are found
across all presets)."""

PACKS = [
    {"id": "business", "en": "Small business / company", "zh": "小企业 / 公司",
     "boss": "owner", "unit": "team", "example": "Liu Consulting",
     "blurb": "operations, bookkeeping, tax prep, customer support, sales, marketing, HR",
     "skills": {"team-collab": "team-collab", "team-data": "team-data", "house-style": "house-style",
                "customer-replies": "customer-replies", "money-records": "money-records",
                "make-slides": "make-slides"},
     "handbook": [("about.md", "what we do, who we serve, owner bio"),
                  ("offer.md", "products/services and what's included"),
                  ("pricing.md", "prices, packages, discount rules"),
                  ("policies.md", "refunds, shipping, hours, response times"),
                  ("voice.md", "how we sound (tone, words we use/avoid)"),
                  ("faq.md", "real customer questions and answers"),
                  ("approved-replies.md", "reply types support may send without asking"),
                  ("chart-of-accounts.md", "expense/income categories for the books")]},
    {"id": "research", "en": "University research lab", "zh": "高校科研实验室",
     "boss": "PI", "unit": "lab", "example": "Liu Lab",
     "blurb": "proposals, manuscripts, literature, HPC computing, data analysis, grants admin",
     "skills": {"team-collab": "team-collab", "team-data": "team-data", "house-style": "house-style-research",
                "fetch-paper": "fetch-paper", "make-slides": "make-slides-research"},
     "handbook": [("bio.md", "PI bio and CV notes"),
                  ("facilities.md", "facilities, equipment, computing boilerplate"),
                  ("boilerplate.md", "grant boilerplate: current & pending, data management, broader impacts"),
                  ("publications.md", "publication list"),
                  ("projects.md", "active projects, funding, collaborators"),
                  ("style.md", "house writing style notes")]},
    {"id": "research-admin", "en": "University research office (research admin)", "zh": "高校科研管理办公室",
     "boss": "director", "unit": "research office", "example": "Office of Research Development",
     "blurb": "funding opportunities, campus expert database, proposal development, news & social media, events, reports",
     "skills": {"team-collab": "team-collab", "team-data": "team-data",
                "house-style": "house-style-research-admin",
                "funding-search": "funding-search", "expert-database": "expert-database",
                "fetch-paper": "fetch-paper", "make-slides": "make-slides"},
     "handbook": [("about.md", "the office: mission, who it serves, director and staff"),
                  ("units.md", "colleges, departments, centers and institutes you serve, with research contacts"),
                  ("priorities.md", "university strategic research priorities and target areas"),
                  ("sponsors.md", "priority agencies, programs, foundations and industry partners"),
                  ("process.md", "internal deadlines, limited-submission process, routing via the sponsored programs office"),
                  ("boilerplate.md", "institutional boilerplate: facilities, institutional profile, F&A, letters of support"),
                  ("contacts.md", "sponsored programs, college research offices, university communications, media relations"),
                  ("style.md", "university news/brand style; social accounts and how each sounds")]},
    {"id": "academic-admin", "en": "University academic leadership (dean / department head)",
     "zh": "高校院系领导（院长 / 系主任）",
     "boss": "dean/head", "unit": "college or department", "example": "Department of Marine, Earth & Atmospheric Sciences",
     "blurb": "faculty affairs & searches, P&T, curriculum & scheduling, students, budget, assessment, governance, advancement, comms",
     "skills": {"team-collab": "team-collab", "team-data": "team-data",
                "house-style": "house-style-academic-admin",
                "confidential-records": "confidential-records", "make-slides": "make-slides"},
     "handbook": [("about.md", "the unit: mission, history, leadership team, org chart"),
                  ("people.md", "faculty and staff roster, ranks, committee and admin roles"),
                  ("policies.md", "bylaws, P&T and post-tenure review guidelines, workload, leave, hiring procedures"),
                  ("programs.md", "degree programs, enrollment, key courses, accreditation status"),
                  ("calendar.md", "academic calendar, review cycles, budget and catalog deadlines"),
                  ("budget.md", "budget summary, faculty lines, space, recurring commitments"),
                  ("priorities.md", "strategic plan, goals, metrics the provost and dean watch"),
                  ("style.md", "how memos, announcements and newsletters should sound")]},
    {"id": "teaching", "en": "Teaching / a course", "zh": "教学 / 课程",
     "boss": "instructor", "unit": "course team", "example": "MEA 591 Generative AI for Science",
     "blurb": "course design, lectures & slides, assignments & rubrics, grading help, student Q&A, LMS",
     "skills": {"team-collab": "team-collab", "team-data": "team-data", "house-style": "house-style-teaching",
                "student-privacy": "student-privacy", "course-materials": "course-materials",
                "make-slides": "make-slides-teaching"},
     "handbook": [("syllabus.md", "the current syllabus (or the institution's template)"),
                  ("policies.md", "grading, late work, attendance, AI-use and integrity policies"),
                  ("schedule.md", "term dates, holidays, exam dates"),
                  ("objectives.md", "course learning objectives"),
                  ("style.md", "how you like materials to look and sound")]},
    {"id": "nonprofit", "en": "Nonprofit / community organization", "zh": "非营利 / 社区组织",
     "boss": "director", "unit": "organization", "example": "Triangle Youth Coding Club",
     "blurb": "programs, grant writing, donors, volunteers, events, communications, board, books",
     "skills": {"team-collab": "team-collab", "team-data": "team-data", "house-style": "house-style-nonprofit",
                "donor-care": "donor-care", "money-records": "money-records",
                "make-slides": "make-slides"},
     "handbook": [("mission.md", "mission, vision, history"),
                  ("programs.md", "programs, who they serve, outcomes so far"),
                  ("boilerplate.md", "organization boilerplate for grants"),
                  ("budget.md", "current budget summary"),
                  ("voice.md", "how the organization sounds"),
                  ("policies.md", "donor privacy, photo consent, volunteer policies")]},
    {"id": "freelance", "en": "Freelancer / creator / consultant", "zh": "自由职业 / 创作者 / 顾问",
     "boss": "owner", "unit": "studio", "example": "Paul Liu Design",
     "blurb": "clients, proposals & invoices, content, social & newsletter, portfolio, books & tax",
     "skills": {"team-collab": "team-collab", "team-data": "team-data", "house-style": "house-style",
                "customer-replies": "customer-replies", "money-records": "money-records",
                "make-slides": "make-slides"},
     "handbook": [("about.md", "who you are, what you do, bio"),
                  ("services.md", "services and what's included"),
                  ("pricing.md", "rates, packages, payment terms"),
                  ("voice.md", "how you sound"),
                  ("portfolio.md", "past projects you can mention (with permission)"),
                  ("faq.md", "client questions and answers")]},
]
DEFAULT = "business"


def get(pid):
    return next((p for p in PACKS if p["id"] == pid), PACKS[0])


def of(cfg):
    return get((cfg or {}).get("pack") or DEFAULT)


def handbook_readme(cfg):
    p = of(cfg)
    lines = ["# {} — handbook".format(cfg["group"]), "",
             "Shared knowledge every member reads. Put here (as .md files):"]
    w = max(len(f) for f, _ in p["handbook"]) + 2
    lines += ["  {:<{w}}{}".format(f, d, w=w) for f, d in p["handbook"]]
    lines += ["", "Members cite this instead of inventing facts, prices or policies.",
              "Keep it current — it is the multiplier that makes every new member cheap.", ""]
    return "\n".join(lines)
