# find_bugs.py - one job: find fixed bugs on GitHub and add them to data/bugs.csv.
# A fixed bug = a merged pull request that says "fixes #N", changes code AND a test file.
import csv
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv()  # reads GITHUB_TOKEN from .env (GitHub allows 5000 lookups an hour with it, 60 without)
TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
FIXES = re.compile(r"(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)


def get(path, **params):
    response = requests.get("https://api.github.com" + path, headers=HEADERS, params=params, timeout=30)
    if response.status_code == 403:
        raise SystemExit("GitHub limit reached. Add GITHUB_TOKEN to .env, or wait an hour.")
    try:
        return response.json()
    except ValueError:
        return {}  # GitHub sent back something that is not JSON. Treat it as "nothing found".


def find_fixes(project, bug_type, how_many):
    # Look at the newest merged pull requests that mention "fix".
    found = []
    search = get("/search/issues", q=f"repo:{project} is:pr is:merged fix in:body", per_page=50)
    for pr in search.get("items", []):
        match = FIXES.search(pr.get("body") or "")
        if not match or len(found) >= how_many:
            continue
        files = [f["filename"] for f in get(f"/repos/{project}/pulls/{pr['number']}/files")]
        is_test = [bool(re.search(r"(^|/)tests?/|(^|/)test_", f)) for f in files]
        if not (any(is_test) and any(not t and f.endswith(".py") for f, t in zip(files, is_test))):
            continue  # we need a code change AND a test from the developers
        issue = get(f"/repos/{project}/issues/{match.group(1)}")
        if "pull_request" in issue or "title" not in issue or not issue.get("body"):
            continue  # it must be a real bug report with text
        fix = get(f"/repos/{project}/pulls/{pr['number']}").get("merge_commit_sha")
        parents = get(f"/repos/{project}/commits/{fix}").get("parents") if fix else None
        if not parents:
            continue  # GitHub has no clear "before" commit for this fix
        before = parents[0]["sha"]
        found.append({"type": bug_type, "set": "main", "project": project,
                      "issue_url": issue["html_url"], "fix_url": pr["html_url"],
                      "fixed_on": pr["closed_at"][:10], "before_fix_commit": before,
                      "fix_commit": fix, "title": issue["title"], "real_bug": "not checked"})
    return found


def add_to_csv(new_bugs):
    # Add bugs we do not have yet. Their IDs are G1, G2, ... (G for "found on GitHub").
    rows = list(csv.DictReader(open("data/bugs.csv", encoding="utf-8")))
    known = {row["issue_url"] for row in rows}
    number = sum(row["id"].startswith("G") for row in rows)
    for bug in new_bugs:
        if bug["issue_url"] not in known:
            number += 1
            rows.append({**bug, "id": f"G{number}"})
            known.add(bug["issue_url"])
    with open("data/bugs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"bugs.csv now has {number} bugs found on GitHub")


if __name__ == "__main__":
    # Try it: python find_bugs.py python-humanize/humanize logic 3
    sys.stdout.reconfigure(encoding="utf-8")  # bug titles can contain characters Windows cannot print
    project, bug_type, how_many = sys.argv[1], sys.argv[2], int(sys.argv[3])
    bugs = find_fixes(project, bug_type, how_many)
    for bug in bugs:
        print(bug["fixed_on"], bug["issue_url"], "-", bug["title"][:70])
    add_to_csv(bugs)
