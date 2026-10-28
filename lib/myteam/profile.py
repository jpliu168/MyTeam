"""The profile: who the team works for, in the human's own words — a company,
a lab, a course, a nonprofit or a freelance practice (see packs.py).

Stored in config.json under "profile", rendered (a) into every member's
skills (`company-profile`, `lab-profile`, ... per preset) so each agent knows
the context without being told, and (b) into handbook/<same>.md for humans.
"""
from . import config, packs

# key, English label, 中文 label, placeholder, multiline
BUSINESS = [
    ("legal_name", "Legal / brand name", "公司/品牌名称", "e.g. MyAiTrade LLC", False),
    ("business", "What the business does", "主营业务", "one or two sentences: what you sell, to whom, and why it's different", True),
    ("industry", "Industry / nature", "行业/性质", "e.g. fintech software, AI trading tools, consulting", False),
    ("entity", "Business type", "企业类型", "sole proprietor, LLC, S-corp, partnership, nonprofit …", False),
    ("location", "Location (state / country)", "所在地（州/国家）", "e.g. Raleigh, North Carolina, USA — matters for tax and law", False),
    ("founded", "Founded", "成立时间", "e.g. 2025", False),
    ("people", "People", "人员", "owner + any humans (e.g. 'just me' / '2 part-time contractors')", False),
    ("products", "Products & services", "产品与服务", "list them, with a line each", True),
    ("customers", "Target customers", "目标客户", "who buys, where they find you", True),
    ("pricing", "Pricing (summary)", "价格（概要）", "plans / rates — details can live in handbook/pricing.md", True),
    ("channels", "Website & channels", "网站与渠道", "website, social accounts, marketplaces", False),
    ("contact", "Public contact & hours", "对外联系方式与营业时间", "support email, phone, hours, time zone", False),
    ("voice", "Brand voice", "品牌语气", "e.g. friendly, plain-spoken, bilingual EN/中文", False),
    ("goals", "Goals right now", "当前目标", "e.g. 100 paying users by June; launch v2", True),
    ("rules", "Owner's rules for the team", "给团队的规矩", "things agents must always / never do for this business", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
RESEARCH = [
    ("legal_name", "Lab name", "实验室名称", "e.g. Liu Lab", False),
    ("institution", "Institution & department", "学校与院系", "e.g. NC State University, Marine, Earth & Atmospheric Sciences", False),
    ("pi", "PI", "负责人（PI）", "name, title, one-line bio", False),
    ("areas", "Research areas", "研究方向", "the questions the lab works on", True),
    ("projects", "Current projects", "在研项目", "one line each: project — goal — status", True),
    ("funding", "Funding", "经费来源", "agencies/awards, numbers and end dates (no account numbers)", True),
    ("people", "People", "成员", "students, postdocs, staff, collaborators", True),
    ("computing", "Computing & data", "计算与数据", "clusters, allocations, key datasets", True),
    ("venues", "Target venues", "目标期刊/会议", "journals, conferences, agencies", False),
    ("deadlines", "Upcoming deadlines", "近期截止日期", "proposals, papers, reports", True),
    ("voice", "Writing style", "写作风格", "e.g. plain, direct, active voice; US spelling", False),
    ("rules", "PI's rules for the lab", "PI 给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
RESEARCH_ADMIN = [
    ("legal_name", "Office name", "办公室名称", "e.g. Office of Research Development", False),
    ("institution", "Institution", "学校", "e.g. NC State University", False),
    ("director", "Director", "负责人", "name, title (e.g. Associate Vice Chancellor for Research Development)", False),
    ("mission", "What the office does", "办公室职能", "one or two sentences", True),
    ("units", "Who you serve", "服务对象", "colleges, departments, centers; faculty count if useful", True),
    ("priorities", "Strategic research priorities", "重点研究方向", "areas the university is pushing", True),
    ("sponsors", "Target sponsors", "重点资助方", "agencies, programs, foundations, industry partners", True),
    ("process", "Internal process & deadlines", "内部流程与截止", "routing lead time, limited-submission process, sponsored programs office", True),
    ("people", "Staff", "人员", "humans in the office and their roles", True),
    ("tools", "Systems & sources", "系统与数据源", "e.g. Pivot-RP, InfoReady, Grants.gov, OpenAlex, RePORTER, directory", True),
    ("channels", "News & social channels", "新闻与社媒渠道", "website, newsletter, LinkedIn/X/Instagram accounts", False),
    ("voice", "Voice", "语气", "e.g. clear, upbeat, AP style, university brand", False),
    ("goals", "Goals this year", "今年目标", "e.g. +20% federal submissions; 3 center-scale bids", True),
    ("rules", "Director's rules for the team", "给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
ACADEMIC_ADMIN = [
    ("legal_name", "College / department name", "学院/系名称", "e.g. Department of Marine, Earth & Atmospheric Sciences", False),
    ("institution", "Institution & college", "学校与学院", "e.g. NC State University, College of Sciences", False),
    ("leader", "Dean / department head", "院长 / 系主任", "name, title, term, one-line bio", False),
    ("mission", "Mission & identity", "使命与定位", "one or two sentences: what the unit is known for", True),
    ("people", "Faculty & staff", "教职工", "counts by rank, key staff and their roles, associate deans/heads", True),
    ("programs", "Degree programs & students", "学位项目与学生", "BS/MS/PhD programs, enrollment, accreditation", True),
    ("research", "Research strengths", "科研优势", "areas, centers, expenditures (roughly)", True),
    ("budget", "Budget & resources (summary)", "预算与资源（概要）", "size, main sources, open lines, space pressures", True),
    ("priorities", "Strategic priorities", "战略重点", "strategic plan goals; what the provost/dean watches", True),
    ("calendar", "Key cycles & deadlines", "关键周期与截止", "P&T, searches, budget requests, catalog, assessment reports", True),
    ("committees", "Committees & governance", "委员会与治理", "standing committees, faculty meeting rhythm, bylaws", True),
    ("channels", "Website & channels", "网站与渠道", "website, newsletter, social accounts, alumni lists", False),
    ("voice", "Voice", "语气", "e.g. collegial, clear, transparent", False),
    ("goals", "Goals this year", "今年目标", "e.g. 3 hires; launch new MS; ABET visit ready", True),
    ("rules", "Dean/head's rules for the team", "给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
GRADUATE = [
    ("legal_name", "Your name & degree", "姓名与学位", "e.g. Jane Doe — PhD student, Atmospheric Sciences", False),
    ("institution", "Institution & program", "学校与项目", "e.g. NC State University, MEAS graduate program", False),
    ("stage", "Year & stage", "年级与阶段", "e.g. 3rd-year PhD, candidacy passed, defending Spring 2028", False),
    ("advisor", "Advisor & committee", "导师与委员会", "names, lab/group, how often you meet", True),
    ("topic", "Research topic", "研究方向", "your dissertation/thesis question in a few sentences", True),
    ("projects", "Current projects & papers", "在研项目与论文", "one line each: project/paper — goal — status — target venue", True),
    ("courses", "Classes this term", "本学期课程", "course — role (taking / TA) — AI-use policy if known", True),
    ("milestones", "Upcoming milestones", "近期学位节点", "quals, proposal, committee meeting, defense, graduation dates", True),
    ("funding", "Funding", "资助", "RA/TA/fellowship and end dates; fellowships you are applying for", True),
    ("computing", "Computing & data", "计算与数据", "clusters, allocations, datasets, code repos", True),
    ("lab", "Lab / group", "实验室 / 课题组", "group name, lab website, labmates, shared resources", True),
    ("news", "People & groups to follow", "关注的人与团队", "your lab, advisor, collaborators, groups in your field; LinkedIn/X/Scholar pages", True),
    ("career", "Career goals", "职业目标", "academia, national lab, industry …; target timeline", False),
    ("voice", "Writing style", "写作风格", "e.g. plain, direct; your advisor's pet peeves", False),
    ("rules", "Your rules for the team", "给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
TEACHING = [
    ("legal_name", "Course code & title", "课程代码与名称", "e.g. MEA 591-004 Generative AI for Science", False),
    ("institution", "Institution & department", "学校与院系", "e.g. NC State University, MEAS", False),
    ("term", "Term & schedule", "学期与上课时间", "e.g. Fall 2026, Tue/Thu 1:30–2:45, room …", False),
    ("instructor", "Instructor & TAs", "授课教师与助教", "names, office hours, contact", True),
    ("students", "Students", "学生", "level, size, majors, background, prerequisites", True),
    ("objectives", "Learning objectives", "学习目标", "what students should be able to do by the end", True),
    ("topics", "Topics / weekly plan", "主题 / 每周安排", "week by week, roughly", True),
    ("assessment", "Assessment & grading", "考核与评分", "weights, rubrics, late policy", True),
    ("lms", "LMS & tools", "教学平台与工具", "e.g. Moodle, Canvas, GitHub Classroom, JupyterHub", False),
    ("ai_policy", "AI-use & integrity policy", "AI 使用与学术诚信政策", "what students may and may not do with AI", True),
    ("voice", "Tone with students", "与学生沟通的语气", "e.g. warm, clear, encouraging", False),
    ("rules", "Instructor's rules for the team", "给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
NONPROFIT = [
    ("legal_name", "Organization name", "组织名称", "e.g. Triangle Youth Coding Club", False),
    ("mission", "Mission", "使命", "one or two sentences", True),
    ("status", "Status & registration", "性质与注册", "e.g. 501(c)(3) public charity, fiscally sponsored, informal club", False),
    ("location", "Location & service area", "所在地与服务范围", "e.g. Wake County, NC", False),
    ("programs", "Programs", "项目", "one line each: program — who it serves — outcomes", True),
    ("people", "People", "人员", "director, staff, board, volunteers", True),
    ("funding", "Funding mix", "资金来源", "grants, donors, events, earned income", True),
    ("channels", "Website & channels", "网站与渠道", "website, newsletter, social", False),
    ("voice", "Voice", "语气", "e.g. hopeful, concrete, community-first", False),
    ("goals", "Goals this year", "今年目标", "e.g. raise $50k; serve 200 students", True),
    ("rules", "Director's rules for the team", "给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
FREELANCE = [
    ("legal_name", "Your name / studio name", "姓名 / 工作室名称", "e.g. Paul Liu Design", False),
    ("business", "What you do", "主要业务", "one or two sentences: services, niche, why clients pick you", True),
    ("services", "Services & packages", "服务与套餐", "one line each", True),
    ("clients", "Ideal clients", "理想客户", "who, where they find you", True),
    ("rates", "Rates & terms", "收费与付款条款", "summary — details in handbook/pricing.md", True),
    ("entity", "Business type & location", "企业类型与所在地", "e.g. single-member LLC, Raleigh NC — matters for tax", False),
    ("availability", "Availability", "可接单时间", "hours, time zone, current capacity", False),
    ("channels", "Portfolio & channels", "作品集与渠道", "website, portfolio, social, marketplaces", False),
    ("voice", "Voice", "语气", "how you sound to clients", False),
    ("goals", "Goals right now", "当前目标", "e.g. 3 retainer clients; raise rates in Q2", True),
    ("rules", "Your rules for the team", "给团队的规矩", "things agents must always / never do", True),
    ("notes", "Anything else", "其他", "background the team should know", True),
]
FIELDS = BUSINESS
BY_PACK = {"business": BUSINESS, "research": RESEARCH, "research-admin": RESEARCH_ADMIN,
           "academic-admin": ACADEMIC_ADMIN, "graduate": GRADUATE, "teaching": TEACHING,
           "nonprofit": NONPROFIT, "freelance": FREELANCE}
TITLE = {"business": ("company-profile", "company profile", "公司简介"),
         "research": ("lab-profile", "lab profile", "实验室简介"),
         "research-admin": ("office-profile", "office profile", "办公室简介"),
         "academic-admin": ("unit-profile", "college/department profile", "院系简介"),
         "graduate": ("student-profile", "graduate student profile", "研究生简介"),
         "teaching": ("course-profile", "course profile", "课程简介"),
         "nonprofit": ("organization-profile", "organization profile", "组织简介"),
         "freelance": ("practice-profile", "practice profile", "业务简介")}


def fields(cfg):
    return BY_PACK.get(packs.of(cfg)["id"], BUSINESS)


def title(cfg):
    return TITLE.get(packs.of(cfg)["id"], TITLE["business"])


def get(cfg):
    return cfg.get("profile") or {}


def filled(cfg):
    return any((v or "").strip() for v in get(cfg).values())


def render_md(cfg, for_agents=False):
    p = get(cfg)
    slug, label, _zh = title(cfg)
    boss = packs.of(cfg)["boss"]
    lines = ["# {} — {}".format(p.get("legal_name") or cfg["group"], label), ""]
    if for_agents:
        lines += ["This is who you work for, as described by the {b}. Use it for".format(b=boss),
                  "context in everything you write; it overrides guesses. Facts, prices,",
                  "policies, dates and promises come only from here, the handbook, or",
                  "the {b}. If something you need is missing, ask the {b}.".format(b=boss), ""]
    for key, label, _zh, _ph, _ml in fields(cfg):
        v = (p.get(key) or "").strip()
        if v:
            lines += ["## " + label, v, ""]
    if not filled(cfg):
        lines += ["(not filled in yet — the {} can add it in Setup)".format(boss), ""]
    return "\n".join(lines)


def skill_text(cfg):
    slug = title(cfg)[0]
    return ("---\nname: {}\ndescription: Who {{{{GROUP}}}} is — what it does, who it serves, "
            "its people, goals and the rules you work by. Read before any task that "
            "touches the outside world.\n---\n\n".format(slug) + render_md(cfg, for_agents=True))


def write_handbook(cfg):
    hb = config.STATE / "handbook"
    hb.mkdir(parents=True, exist_ok=True)
    (hb / (title(cfg)[0] + ".md")).write_text(
        "<!-- generated from Setup → profile; edit it there -->\n" + render_md(cfg))
