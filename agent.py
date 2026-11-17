# agent.py - one job: run all the steps in order to reproduce one bug.
import os
import sys
import time

from check import is_match, why_no_match
from docker_run import prepare_box, run_test
from download import get_bug, get_code, get_issue
from llm import ask_json
from pick_files import pick_files, read_bug
from prompts import write_test_prompt
from save import save_result
from verify import passes_after_fix

MAX_TRIES = 4


def read_files(paths, folder):
    # Put the picked files into one text, each with its name on top.
    parts = []
    for path in paths:
        text = open(path, encoding="utf-8").read()
        parts.append(f"--- {os.path.relpath(path, folder)} ---\n{text}")
    return "\n\n".join(parts)


def try_once(folder, bug_id, issue, code, history, report_may_be_wrong):
    # One try: Gemini writes a test, then we run it in the sealed box.
    try:
        answer = ask_json(write_test_prompt(issue, code, history, report_may_be_wrong))
        guess, test_code = answer["guess"], answer["test_code"]
    except (ValueError, KeyError) as error:
        # Gemini's answer was not in the right format. Count it as a failed try.
        return {"guess": "(bad answer from Gemini)", "test_code": "", "output": f"Not valid JSON: {error}"}
    with open(os.path.join(folder, "test_bug.py"), "w", encoding="utf-8") as f:
        f.write(test_code)
    return {"guess": guess, "test_code": test_code, "output": run_test(folder, bug_id),
            "new_error_type": answer.get("error_type")}  # only used when the report may be wrong


def reproduce(bug_text):
    start = time.time()
    bug = get_bug(bug_text)  # a bug ID like L1, or a GitHub issue link
    bug_id = bug["id"]
    folder = os.path.join("workspace", bug_id)

    print("1. Getting the code and the bug report")
    get_code(bug, folder)
    get_issue(bug, folder)
    # Set up the room once. A few old bugs need packages from their own date (package_date in bugs.csv).
    prepare_box(folder, bug_id, bug.get("package_date", ""))

    print("2. Gemini reads the bug")
    info = read_bug(folder)
    print("   Error to find:", info["error_type"])

    files = pick_files(folder, info["keywords"], info["file_names"])
    names = [os.path.relpath(f, folder).replace("\\", "/") for f in files]
    print("3. Files picked:", names)

    issue = open(os.path.join(folder, "issue.txt"), encoding="utf-8").read()
    code = read_files(files, folder)
    tries = []  # every try so far. The failed ones are shown to Gemini next time.
    status = "not reproduced"
    error_changes = []  # written down if Gemini says the report named the wrong error

    for attempt in range(1, MAX_TRIES + 1):
        print(f"4. Try {attempt}: Gemini guesses the cause, the test runs in the sealed box")
        # After 2 passed tests in a row, tell Gemini the report itself may be wrong.
        two_passed = len(tries) >= 2 and all("PASSED" in t["reason"] for t in tries[-2:])
        one_try = try_once(folder, bug_id, issue, code, tries, two_passed)
        new_type = one_try.pop("new_error_type", None)
        if two_passed and new_type and new_type != info["error_type"]:
            print(f"   Gemini thinks the report is wrong: looking for {new_type}, not {info['error_type']}")
            error_changes.append(f"{info['error_type']} -> {new_type}")
            info["error_type"] = new_type
        one_try["match"] = is_match(one_try["output"], info["error_type"])
        one_try["reason"] = "" if one_try["match"] else why_no_match(one_try["output"], info["error_type"])
        tries.append(one_try)
        print("   Guess:", one_try["guess"])
        if one_try["match"]:
            status = "reproduced"
            break
        print("   No match:", one_try["reason"])

    print(f"5. {status.upper()} after {len(tries)} tries")

    # Scoring only: does the winning test pass on the developers' real fix?
    verified = None  # stays None for links: there is no known fix to compare with
    if status == "reproduced" and not bug["fix_commit"]:
        print("6. No known fix for this bug, so only the judge's 3 rules were used")
    if status == "reproduced" and bug["fix_commit"]:
        verified, fix_output = passes_after_fix(bug, folder, tries[-1]["test_code"])
        tries[-1]["output_after_fix"] = fix_output
        print("6. Check with the real fix:", "PASSED, real proof" if verified else "FAILED, the test is not about this bug")

    path = save_result({
        "bug": bug_id, "issue": bug["issue_url"], "error_to_find": info["error_type"], "files_picked": names,
        "status": status, "verified_with_fix": verified, "error_changes": error_changes,
        "seconds": round(time.time() - start), "tries": tries,
    })
    print("7. Saved to", path)


if __name__ == "__main__":
    # Try it: python agent.py L1   or   python agent.py https://github.com/owner/repo/issues/123
    try:
        reproduce(sys.argv[1])
    except RuntimeError as error:
        print("Stopped:", error)
