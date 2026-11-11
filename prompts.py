# prompts.py - one job: hold the questions we ask Gemini.

# Question 1: read the bug report. The report text is added at the end.
READ_BUG = """You are helping reproduce a bug in a Python project.
Read the bug report below. Reply with only JSON, nothing else, like this:
{"error_type": "OverflowError", "keywords": ["word1", "word2"], "file_names": ["file.py"]}

error_type: the Python error the bug causes.
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


def write_test_prompt(issue, code, history):
    # Join question 2, the bug report and the picked files into one message.
    text = WRITE_TEST + "\nBug report:\n" + issue + "\n\nCode:\n" + code
    # From try 2 on, add what went wrong before, so Gemini can do better.
    if history:
        text += "\n\nThese earlier tries did not work. Try a different cause or a different test.\n"
        for number, old in enumerate(history, start=1):
            text += f"\nTry {number}, guess: {old['guess']}\nWhat the test printed:\n{old['output'][-2000:]}\n"
    return text
