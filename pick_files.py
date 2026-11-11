# pick_files.py - one job: find the few files most related to the bug.
import os
import sys

from llm import ask_json
from prompts import READ_BUG

SKIP_FOLDERS = [".git", "tests", "docs"]


def read_bug(folder):
    # Step 1: Gemini reads the bug report and tells us what to search for.
    with open(os.path.join(folder, "issue.txt"), encoding="utf-8") as f:
        return ask_json(READ_BUG + f.read())


def pick_files(folder, keywords, file_names):
    # Steps 2 and 3: score every .py file, then keep the best 3.
    mentioned = [os.path.basename(name) for name in file_names]
    scores = {}
    for root, folders, files in os.walk(folder):
        folders[:] = [f for f in folders if f not in SKIP_FOLDERS]
        for name in files:
            if name.endswith(".py") and name != "test_bug.py":  # never show Gemini our own test
                path = os.path.join(root, name)
                text = open(path, encoding="utf-8", errors="ignore").read()
                score = sum(text.count(word) for word in keywords)
                if name in mentioned:
                    score += 10
                scores[path] = score
    best = sorted(scores, key=scores.get, reverse=True)[:3]
    return [path for path in best if scores[path] > 0]


if __name__ == "__main__":
    # Try it: python pick_files.py L1
    folder = os.path.join("workspace", sys.argv[1])
    bug = read_bug(folder)
    print("Error:   ", bug["error_type"])
    print("Keywords:", bug["keywords"])
    print("Files:   ", pick_files(folder, bug["keywords"], bug["file_names"]))
