# check.py - one job: decide if a test really showed the bug. Python decides, not the AI.
import re


def is_match(output, error_type):
    # Rule 1: the test ran and failed. A broken test shows ERROR, not FAILED.
    ran = "FAILED test_bug.py" in output

    # Rule 2: the error is the one from the bug report. Error lines start with "E   ".
    same_error = f"E   {error_type}" in output
    # When an assert line fails, pytest prints "E   assert 100 == 110" instead of the word AssertionError.
    if error_type == "AssertionError" and "E   assert " in output:
        same_error = True
    # A freeze bug: after 20 seconds pytest-timeout stops the test and prints "E   Failed: Timeout".
    if error_type == "Timeout" and "E   Failed: Timeout" in output:
        same_error = True

    # Rule 3 (also for freezes: the line it was stuck on must be in the project's code): the error passed through the project's own code, not only through test_bug.py.
    # Each step of the error looks like "src/humanize/time.py:151: in naturaldelta".
    files = re.findall(r"^(\S+\.py):\d+: in ", output, re.MULTILINE)
    project_files = [f for f in files if f != "test_bug.py" and not f.startswith("/")]
    # A wrong-answer bug fails with AssertionError inside test_bug.py, so rule 3 cannot apply.
    # For those, the check against the real fix (verify.py) is the proof instead.
    in_project = len(project_files) > 0 or error_type == "AssertionError"

    return ran and same_error and in_project


def why_no_match(output, error_type):
    # Turn a failed try into one plain sentence, so Gemini knows WHY it did not work.
    last_line = output.strip().splitlines()[-1] if output.strip() else ""
    if output.startswith("Not valid JSON"):
        return "Your answer was not valid JSON. Reply with only the JSON."
    if "passed" in last_line and "failed" not in last_line:
        return "Your test PASSED, so the bug did NOT happen. Try a different input or a different idea."
    if "FAILED test_bug.py" not in output:
        return "Your test could not run (a typo, a bad import, or it got stuck). Fix the test itself."
    errors = re.findall(r"^E   (\w+)", output, re.MULTILINE)
    found = errors[0] if errors else "an unknown error"
    found = {"assert": "AssertionError", "Failed": "Timeout"}.get(found, found)  # pytest's own words
    if found == error_type:
        return "It failed with the right error, but not inside the project's code. Call the project's code."
    return f"It failed with {found}, but the bug is {error_type}. Look for a different cause."
