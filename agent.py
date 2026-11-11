# agent.py - one job: run all the steps in order to reproduce one bug.
import os
import sys
import time

from check import is_match
from docker_run import run_test
from download import find_bug, get_code, get_issue
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


def try_once(folder, bug_id, issue, code, history):
    # One try: Gemini writes a test, then we run it in the sealed box.
    try:
        answer = ask_json(write_test_prompt(issue, code, history))
        guess, test_code = answer["guess"], answer["test_code"]
    except (ValueError, KeyError) as error:
        # Gemini's answer was not in the right format. Count it as a failed try.
        return {"guess": "(bad answer from Gemini)", "test_code": "", "output": f"Not valid JSON: {error}"}
    with open(os.path.join(folder, "test_bug.py"), "w", encoding="utf-8") as f:
        f.write(test_code)
    return {"guess": guess, "test_code": test_code, "output": run_test(folder, bug_id)}


def reproduce(bug_id):
    start = time.time()
    bug = find_bug(bug_id)
    folder = os.path.join("workspace", bug_id)

    print("1. Getting the code and the bug report")
    get_code(bug, folder)
    get_issue(bug, folder)

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

    for attempt in range(1, MAX_TRIES + 1):
        print(f"4. Try {attempt}: Gemini guesses the cause, the test runs in the sealed box")
        one_try = try_once(folder, bug_id, issue, code, tries)
        one_try["match"] = is_match(one_try["output"], info["error_type"])
        tries.append(one_try)
        print("   Guess:", one_try["guess"])
        if one_try["match"]:
            status = "reproduced"
            break
        print("   No match.")

    print(f"5. {status.upper()} after {len(tries)} tries")

    # Scoring only: does the winning test pass on the developers' real fix?
    verified = None
    if status == "reproduced":
        verified, fix_output = passes_after_fix(bug, folder, tries[-1]["test_code"])
        tries[-1]["output_after_fix"] = fix_output
        print("6. Check with the real fix:", "PASSED, real proof" if verified else "FAILED, the test is not about this bug")

    path = save_result({
        "bug": bug_id, "error_to_find": info["error_type"], "files_picked": names,
        "status": status, "verified_with_fix": verified,
        "seconds": round(time.time() - start), "tries": tries,
    })
    print("7. Saved to", path)


if __name__ == "__main__":
    # Try it: python agent.py L1
    reproduce(sys.argv[1])
