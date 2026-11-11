# verify.py - one job: check a test against the developers' real fix (the "answer key").
# A good test fails on the old code and PASSES on the fixed code. Used only for scoring.
import os
import re
import subprocess

from docker_run import run_test


def passes_after_fix(bug, folder, test_code):
    # Move the code forward to the commit with the real fix, run the same test, then move back.
    subprocess.run(["git", "checkout", "-q", bug["fix_commit"]], cwd=folder, check=True)
    try:
        with open(os.path.join(folder, "test_bug.py"), "w", encoding="utf-8") as f:
            f.write(test_code)
        output = run_test(folder, bug["id"])
    finally:
        subprocess.run(["git", "checkout", "-q", bug["before_fix_commit"]], cwd=folder, check=True)
    last_line = output.strip().splitlines()[-1] if output.strip() else ""
    passed = re.search(r"\d+ passed", last_line) and "failed" not in last_line and "error" not in last_line
    return bool(passed), output
