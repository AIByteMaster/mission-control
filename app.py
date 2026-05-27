from flask import Flask, render_template
import os
import re
from datetime import datetime

app = Flask(__name__)

AGENT_MEMORY = os.path.expanduser("~/agent-memory")
EARNINGS_FILE = os.path.expanduser("~/agent-memory/fiverr/fiverr-earnings.md")

def read_md(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except:
        return ""

def parse_todos(md_content):
    """Parse [ ] and [x] items from markdown"""
    todos = {'pending': [], 'completed': []}
    lines = md_content.split('\n')
    for line in lines:
        # Match - [ ] or - [x] pattern
        match = re.match(r'^-\s+\[([ x])\]\s+(.+)$', line.strip())
        if match:
            status = 'completed' if match.group(1) == 'x' else 'pending'
            todos[status].append(match.group(2).strip())
    return todos

def parse_goals_table(md_content):
    """Extract the key metrics table from goals"""
    table = []
    in_table = False
    for line in md_content.split('\n'):
        if re.match(r'^\|\s*Goal', line):
            in_table = True
            continue
        if in_table and re.match(r'^\|[-:\s]+\|', line):
            continue
        if in_table and re.match(r'^\|.*\|', line):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 4:
                table.append(parts)
        elif in_table and line.strip() == '':
            break
    return table

def parse_fiverr_earnings(md_content):
    """Parse key financial metrics from fiverr earnings file"""
    data = {}
    # Extract total earned
    match = re.search(r'\|\s*\*?\*?Total Earned.*?\|\s*\*?\$?([0-9,]+\.?\d*)', md_content)
    if match:
        data['total_earned'] = match.group(1)
    # Extract expenses
    match = re.search(r'Expenses to date\s*\|\s*\$?([0-9,]+\.?\d*)', md_content)
    if match:
        data['expenses'] = match.group(1)
    # Extract net earnings
    match = re.search(r'Net earnings\s*\|\s*~\$?([0-9,]+\.?\d*)', md_content)
    if match:
        data['net_earnings'] = match.group(1)
    # Extract withdrawn
    match = re.search(r'Withdrawn to date\s*\|\s*\$?([0-9,]+\.?\d*)', md_content)
    if match:
        data['withdrawn'] = match.group(1)
    # Extract pending
    match = re.search(r'Pending/future payments\s*\|\s*\$?([0-9,]+\.?\d*)', md_content)
    if match:
        data['pending'] = match.group(1)
    return data

@app.route('/')
def index():
    # Read markdown files
    todo_active = read_md(f"{AGENT_MEMORY}/todo/ACTIVE.md")
    todo_archive = read_md(f"{AGENT_MEMORY}/todo/ARCHIVE.md")
    goals_active = read_md(f"{AGENT_MEMORY}/goals/ACTIVE.md")
    goals_archive = read_md(f"{AGENT_MEMORY}/goals/ARCHIVE.md")
    earnings_content = read_md(EARNINGS_FILE) if os.path.exists(EARNINGS_FILE) else ""
    
    # Parse data
    todos = parse_todos(todo_active)
    goals_table = parse_goals_table(goals_active)
    earnings = parse_fiverr_earnings(earnings_content) if earnings_content else {}
    
    # Projects list
    projects = {
        'internal': [
            {'name': 'NexomateAI', 'desc': 'AI automation for insurance agencies', 'status': 'Active'},
            {'name': 'Task-inbox', 'desc': 'General task management', 'status': 'Active'},
            {'name': 'Bella-generalagent', 'desc': 'General agent assistant', 'status': 'Active'},
            {'name': 'ECC', 'desc': 'Everything-Claude-Code deep dive', 'status': 'Review'},
            {'name': 'VPS/Nextcloud', 'desc': 'Self-hosted cloud infrastructure', 'status': 'Active'},
        ],
        'external': [
            {'name': 'Fiverr Gigs', 'desc': '7 active gigs (n8n, automation)', 'status': 'Active'},
        ]
    }
    
    return render_template('index.html',
                         todos=todos,
                         goals_table=goals_table,
                         goals_active=goals_active,
                         projects=projects,
                         earnings=earnings,
                         has_earnings=bool(earnings))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)