from flask import Flask, render_template
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

app = Flask(__name__)

ROOT = Path(__file__).resolve().parent
SNAPSHOT_MEMORY = ROOT / "data" / "agent-memory"
LOCAL_MEMORY = Path(os.path.expanduser("~/agent-memory"))


def memory_root():
    """Use live local memory when available; use committed snapshot on Vercel."""
    if (LOCAL_MEMORY / "todo" / "ACTIVE.md").exists():
        return LOCAL_MEMORY
    return SNAPSHOT_MEMORY


def read_md(relative_path):
    path = memory_root() / relative_path
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_last_updated(*contents):
    for content in contents:
        match = re.search(r"\*\*Last updated:\*\*\s*([^\n]+)", content)
        if match:
            return match.group(1).strip()
        match = re.search(r"\*\*Updated:\*\*\s*([^\n]+)", content)
        if match:
            return match.group(1).strip()
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def split_inline_date(text, fallback="Unknown"):
    """Extract `(added: YYYY-MM-DD)` metadata without showing raw markup."""
    date_match = re.search(r"\s*[\[(]added:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})[\])]", text, flags=re.I)
    added = date_match.group(1) if date_match else fallback
    if date_match:
        text = (text[:date_match.start()] + text[date_match.end():]).strip()
    return text, added


def parse_todos(*contents):
    todos = {"pending": [], "completed": []}
    for content in contents:
        fallback_date = extract_last_updated(content)
        for line in content.splitlines():
            match = re.match(r"^\s*-\s+\[([ xX])\]\s+(.+?)\s*$", line)
            if not match:
                continue
            task = re.sub(r"\s+\(pending\)\s*$", "", match.group(2).strip())
            task, added = split_inline_date(task, fallback_date)
            item = {"text": task, "added": added}
            if match.group(1).lower() == "x":
                todos["completed"].append(item)
            else:
                todos["pending"].append(item)
    return todos


def parse_goals(content):
    goals = []
    current = None
    for line in content.splitlines():
        heading = re.match(r"^-\s+\[([ xX])\]\s+\*\*(.+?)\*\*", line.strip())
        if heading:
            if current:
                goals.append(current)
            current = {
                "done": heading.group(1).lower() == "x",
                "title": heading.group(2).strip(),
                "started": "",
                "target_date": "",
                "status": "",
                "roadmap": "",
            }
            continue
        if current:
            detail = re.match(r"^\s*-\s+\*(Started|Target date|Status|Roadmap):\*\s*(.+?)\s*$", line)
            if detail:
                key = detail.group(1).lower().replace(" ", "_")
                current[key] = detail.group(2).strip()
    if current:
        goals.append(current)
    return goals


def parse_goals_table(content):
    table = []
    in_table = False
    for line in content.splitlines():
        if re.match(r"^\|\s*Goal\s*\|", line):
            in_table = True
            continue
        if in_table and re.match(r"^\|[-:\s|]+$", line):
            continue
        if in_table and re.match(r"^\|.*\|", line):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 4:
                table.append(parts[:4])
        elif in_table and not line.strip():
            break
    return table


def money_value(text):
    match = re.search(r"\$?([0-9][0-9,]*(?:\.\d+)?)", text or "")
    return match.group(1) if match else "0"


def parse_fiverr_earnings(content):
    data = {}
    for line in content.splitlines():
        if not line.startswith("|") or "---" in line or "Metric" in line:
            continue
        cells = [c.strip().replace("**", "") for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        metric, amount = cells[0].lower(), cells[1]
        if "total earned" in metric:
            data["total_earned"] = money_value(amount)
        elif "expenses" in metric:
            data["expenses"] = money_value(amount)
        elif "net earnings" in metric:
            data["net_earnings"] = money_value(amount)
        elif "withdrawn" in metric:
            data["withdrawn"] = money_value(amount)
        elif "balance" in metric:
            data["balance"] = money_value(amount)
        elif "pending" in metric or "future" in metric:
            data["pending"] = money_value(amount)
    return data


def parse_projects(content):
    projects = {"internal": [], "external": []}
    for line in content.splitlines():
        match = re.match(r"^-\s+\[([^\]]+)\]\s+([^|]+)\|\s*([^|]+)\|\s*added:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*\|\s*group:\s*(internal|external)", line.strip(), flags=re.I)
        if not match:
            continue
        status, name, desc, added, group = match.groups()
        projects[group.lower()].append({
            "name": name.strip(),
            "desc": desc.strip(),
            "status": status.strip(),
            "added": added.strip(),
        })
    return projects if (projects["internal"] or projects["external"]) else None


def check_url(name, url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MissionControl/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.getcode()
        if 200 <= code < 400:
            return {"name": name, "status": "Online", "class": "online", "detail": str(code)}
        return {"name": name, "status": "Issue", "class": "issue", "detail": str(code)}
    except Exception as exc:
        return {"name": name, "status": "Down", "class": "down", "detail": exc.__class__.__name__}


@app.route("/")
def index():
    todo_active = read_md("todo/ACTIVE.md")
    todo_archive = read_md("todo/ARCHIVE.md")
    goals_active = read_md("goals/ACTIVE.md")
    earnings_content = read_md("fiverr/fiverr-earnings.md")
    projects_content = read_md("projects/ACTIVE.md")

    todos = parse_todos(todo_active, todo_archive)
    goals = parse_goals(goals_active)
    goals_table = parse_goals_table(goals_active)
    earnings = parse_fiverr_earnings(earnings_content)

    projects = parse_projects(projects_content) or {
        "internal": [
            {"name": "NexomateAI", "desc": "AI automation for insurance agencies", "status": "Active", "added": "2026-05-24"},
            {"name": "Mission Control", "desc": "Live operations dashboard", "status": "Active", "added": "2026-05-27"},
            {"name": "Task-inbox", "desc": "Telegram task tracker", "status": "Active", "added": "2026-05-27"},
            {"name": "Bella-generalagent", "desc": "General agent assistant", "status": "Active", "added": "2026-05-27"},
            {"name": "VPS/Nextcloud", "desc": "Self-hosted cloud infrastructure", "status": "Active", "added": "2026-05-27"},
        ],
        "external": [
            {"name": "Fiverr Gigs", "desc": "7 active gigs, AI automation focus", "status": "Active", "added": "2026-05-24"},
            {"name": "X Brand", "desc": "Grow audience → NexomateAI clients", "status": "Active", "added": "2026-05-24"},
        ],
    }

    health = [
        check_url("Nextcloud", "https://vmi3327103.contaboserver.net"),
        check_url("Website (nexomateai.com)", "https://nexomateai.com"),
        {"name": "Fiverr Gigs", "status": "Tracked", "class": "online", "detail": "7 gigs"},
    ]

    return render_template(
        "index.html",
        todos=todos,
        goals=goals,
        goals_table=goals_table,
        projects=projects,
        earnings=earnings,
        health=health,
        data_source="local live files" if memory_root() == LOCAL_MEMORY else "deployed snapshot",
        last_updated=extract_last_updated(todo_active, goals_active, earnings_content),
        has_earnings=bool(earnings),
    )


@app.route("/healthz")
def healthz():
    return {"ok": True, "data_source": str(memory_root())}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
