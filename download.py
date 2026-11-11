# download.py - one job: get a project's code (with the bug) and its bug report.
import csv
import os
import subprocess
import sys

import requests


def find_bug(bug_id):
    # Look up one row in data/bugs.csv, for example "L1".
    with open("data/bugs.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] == bug_id:
                return row
    raise SystemExit(f"Bug {bug_id} is not in data/bugs.csv")


def get_code(bug, folder):
    # Clone the project once, then go back to the commit before the fix.
    if not os.path.exists(folder):
        url = f"https://github.com/{bug['project']}.git"
        subprocess.run(["git", "clone", "-q", url, folder], check=True)
    subprocess.run(["git", "checkout", "-q", bug["before_fix_commit"]], cwd=folder, check=True)


def get_issue(bug, folder):
    # Ask GitHub for the issue and save its title and text.
    number = bug["issue_url"].rstrip("/").split("/")[-1]
    api_url = f"https://api.github.com/repos/{bug['project']}/issues/{number}"
    issue = requests.get(api_url, timeout=30).json()
    with open(os.path.join(folder, "issue.txt"), "w", encoding="utf-8") as f:
        f.write(issue["title"] + "\n\n" + (issue["body"] or ""))


if __name__ == "__main__":
    # Try it: python download.py L1
    bug = find_bug(sys.argv[1])
    folder = os.path.join("workspace", bug["id"])
    get_code(bug, folder)
    get_issue(bug, folder)
    print(f"Code and issue saved in {folder}")
