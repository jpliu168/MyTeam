"""working / blocked / idle from a member session's visible tail (herdr-style)."""
import re

BLOCKED = [
    r"[Pp]assword\s*:", r"[Pp]asscode", r"\bDuo\b",
    r"Login expired", r"Please run /login",
    r"\(y/n\)|\[y/N\]|\[Y/n\]", r"Do you want", r"Allow .*\?",
    r"press (enter|any key)", r"permission", r"trust this",
    r"Do you trust", r"Yes, proceed", r"^\s*[❯›>]\s*1\.\s",
]
WORKING = [
    r"esc to interrupt", r"ctrl\+c to stop",
    r"Working|Thinking|Running|Compacting",
    r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]",
    r"[✢✳✶✻*]\s+\w+ing",
    r"\.\.\.\s*$",
]
GLYPH = {"working": "●", "blocked": "◐", "idle": "○", "gone": "✗"}


def classify(lines):
    if not lines:
        return "idle"
    text = "\n".join(lines[-12:])
    for p in BLOCKED:
        if re.search(p, text):
            return "blocked"
    for p in WORKING:
        if re.search(p, text):
            return "working"
    return "idle"


def blocked_reason(lines):
    """The line that made a session look blocked (for the briefing)."""
    for line in lines[-12:]:
        for p in BLOCKED:
            if re.search(p, line):
                return re.sub(r"^[\s│|>❯›]+", "", line).strip()
    return ""


# Agent-CLI chrome that is noise in a reply: rules, prompts, mode banners,
# timers. Real reply text never looks like this.
_CHROME = [
    r"^\s*[─━═—_\-│|╭╮╰╯┌┐└┘]+\s*$",      # rules / box edges
    r"^\s*[❯›>]\s*$",                        # empty input prompt
    r"auto mode (on|off)|shift\+tab to cycle|\? for shortcuts",
    r"esc to interrupt|ctrl\+c to stop",
    r"Image in\s*$|^\s*clipboard\s*·|ctrl\+v to paste",
    r"^\s*[✢✳✶✻✽*·]\s+\w+(ed|ing)\b.*\d+s\b",   # "✻ Sautéed for 5s · done"
    r"^\s*⎿?\s*Tip:",
]


def clean_reply(lines, keep=14):
    # start after the message we injected ("[myteam msg from owner] ..."),
    # skipping its wrapped continuation lines, so the reply is just the reply
    marks = [i for i, l in enumerate(lines) if "[myteam " in l]
    if marks:
        i = marks[-1] + 1
        while i < len(lines) and lines[i].strip():
            i += 1
        if any(l.strip() for l in lines[i:]):
            lines = lines[i:]
    out = []
    for l in lines:
        if any(re.search(p, l) for p in _CHROME):
            continue
        if not l.strip() and (not out or not out[-1].strip()):
            continue                      # collapse runs of blank lines
        out.append(l)
    while out and not out[-1].strip():
        out.pop()
    while out and not out[0].strip():
        out.pop(0)
    return out[-keep:]
