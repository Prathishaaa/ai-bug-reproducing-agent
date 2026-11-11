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

    # Rule 3: the error passed through the project's own code, not only through test_bug.py.
    # Each step of the error looks like "src/humanize/time.py:151: in naturaldelta".
    files = re.findall(r"^(\S+\.py):\d+: in ", output, re.MULTILINE)
    project_files = [f for f in files if f != "test_bug.py" and not f.startswith("/")]
    # A wrong-answer bug fails with AssertionError inside test_bug.py, so rule 3 cannot apply.
    # For those, the check against the real fix (verify.py) is the proof instead.
    in_project = len(project_files) > 0 or error_type == "AssertionError"

    return ran and same_error and in_project
