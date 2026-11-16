# prompts.py - one job: hold the questions we ask Gemini.

# Question 1: read the bug report. The report text is added at the end.
READ_BUG = """You are helping reproduce a bug in a Python project.
Read the bug report below. Reply with only JSON, nothing else, like this:
{"error_type": "OverflowError", "keywords": ["word1", "word2"], "file_names": ["file.py"]}

error_type: the Python error the bug causes. If it gives a wrong result instead, use AssertionError.
keywords: 2 to 5 function or variable names to search the code for.
file_names: any .py files the report mentions, or an empty list.

Bug report:
"""

# Question 2: guess the cause and write a test. The report and code are added at the end.
WRITE_TEST = """You are helping reproduce a bug in a Python project.
Read the bug report and the code below. Guess the cause, then write a pytest test
that fails because of this bug now, and would pass once the bug is fixed.
Reply with only JSON, nothing else, like this:
{"guess": "one sentence about the cause", "test_code": "the full test file"}

Rules for test_code:
- It is saved as test_bug.py in the project folder, with one function named test_bug.
- Import the project the way a user would, for example "import humanize".
- Call the project's own code. Never raise the error yourself.
- No internet, no extra packages. Keep it short.
"""


# Added after 2 passed tests in a row: maybe the report itself is wrong or out of date.
REPORT_MAY_BE_WRONG = """
Your last 2 tests PASSED, so the bug report may be wrong or out of date.
Read the code and find what really goes wrong for the case in the report.
Do not only check that it does not crash. Check that the exact result is correct,
for example: assert the output equals what a user would expect.
If the real problem is a different error, add it to your JSON, like this:
{"guess": "...", "test_code": "...", "error_type": "AssertionError"}
"""


def write_test_prompt(issue, code, history, report_may_be_wrong=False):
    # Join question 2, the bug report and the picked files into one message.
    text = WRITE_TEST + "\nBug report:\n" + issue + "\n\nCode:\n" + code
    # From try 2 on, add what went wrong before and WHY, so Gemini tries a new idea.
    if history:
        text += "\n\nThese earlier tries did not work. Use a NEW idea, not the same one again.\n"
        for number, old in enumerate(history, start=1):
            text += f"\nTry {number}, guess: {old['guess']}\nWhy it did not work: {old['reason']}\n"
            text += f"What the test printed:\n{old['output'][-2000:]}\n"
    if report_may_be_wrong:
        text += REPORT_MAY_BE_WRONG
    return text
