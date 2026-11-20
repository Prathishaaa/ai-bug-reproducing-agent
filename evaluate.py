# evaluate.py - one job: run the agent on every real bug, then write results/summary.csv.
import csv
import json
import os
import subprocess

from agent import reproduce


def real_bugs():
    # The main bugs that passed the hand check (real_bug = yes in data/bugs.csv).
    with open("data/bugs.csv", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if row["set"] == "main" and row["real_bug"] == "yes"]


def load(bug_id):
    # Read a saved result. Old results without the real-fix check are run again.
    path = os.path.join("results", bug_id + ".json")
    if not os.path.exists(path):
        return None
    result = json.load(open(path, encoding="utf-8"))
    return result if "verified_with_fix" in result else None


def write_summary(bugs):
    rows = []
    for bug in bugs:
        result = load(bug["id"])
        if result:
            proven = result["status"] == "reproduced" and result["verified_with_fix"] is True
            rows.append({"bug": bug["id"], "type": bug["type"], "reproduced": "yes" if proven else "no",
                         "tries": len(result["tries"]), "seconds": result["seconds"]})
    with open("results/summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["bug", "type", "reproduced", "tries", "seconds"])
        writer.writeheader()
        writer.writerows(rows)

    done = [r for r in rows if r["reproduced"] == "yes"]
    first_try = [r for r in done if r["tries"] == 1]
    print(f"\nRun so far: {len(rows)} of {len(bugs)} bugs")
    print(f"Reproduced on try 1:  {len(first_try)} of {len(rows)}")
    print(f"Reproduced in any try: {len(done)} of {len(rows)}")


if __name__ == "__main__":
    # Try it: python evaluate.py   (run it again later to continue where it stopped)
    bugs = real_bugs()
    try:
        for bug in bugs:
            if load(bug["id"]):
                continue  # already done
            print(f"\n===== {bug['id']}")
            try:
                reproduce(bug["id"])
            except Exception as error:
                print(f"{bug['id']} could not run: {error}. It will be tried again next time.")
            # Delete this bug's room to save disk. The result is saved, and the room is rebuilt if needed.
            subprocess.run(["docker", "rmi", "-f", "bug-box-" + bug["id"].lower()], capture_output=True)
    finally:
        write_summary(bugs)  # also runs if the Gemini limit stops us early
