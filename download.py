# download.py - one job: get a project's code (with the bug) and its bug report.
import csv
import os
import re
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


def bug_from_link(link):
    # Turn https://github.com/OWNER/REPO/issues/NUMBER into the same info a bugs.csv row has.
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", link)
    if not match:
        raise SystemExit("Please give an issue link like https://github.com/owner/repo/issues/123")
    owner, repo, number = match.groups()
    # No known fix, so there are no commits to go back to.
    return {"id": f"{owner}-{repo}-{number}".lower(), "project": f"{owner}/{repo}",
            "issue_url": link, "before_fix_commit": "", "fix_commit": ""}


def get_bug(text):
    # Accept a bug ID from our list (like L1) or a GitHub issue link.
    return bug_from_link(text) if text.startswith("http") else find_bug(text)


def get_code(bug, folder):
    # Clone the project once. For bugs from our list, go back to the commit before the fix.
    if not os.path.exists(folder):
        url = f"https://github.com/{bug['project']}.git"
        subprocess.run(["git", "clone", "-q", url, folder], check=True)
    if bug["before_fix_commit"]:
        subprocess.run(["git", "checkout", "-q", bug["before_fix_commit"]], cwd=folder, check=True)


def get_issue(bug, folder):
    # Ask GitHub for the issue and save its title and text.
    number = bug["issue_url"].rstrip("/").split("/")[-1]
    api_url = f"https://api.github.com/repos/{bug['project']}/issues/{number}"
    issue = requests.get(api_url, timeout=30).json()
    if "title" not in issue:
        raise SystemExit(f"GitHub could not find this issue: {issue.get('message', 'unknown error')}")
    if "pull_request" in issue:
        raise SystemExit("This link is a pull request. Please give an issue link.")
    with open(os.path.join(folder, "issue.txt"), "w", encoding="utf-8") as f:
        f.write(issue["title"] + "\n\n" + (issue["body"] or ""))


if __name__ == "__main__":
    # Try it: python download.py L1   or   python download.py https://github.com/owner/repo/issues/123
    bug = get_bug(sys.argv[1])
    folder = os.path.join("workspace", bug["id"])
    get_code(bug, folder)
    get_issue(bug, folder)
    print(f"Code and issue saved in {folder}")
