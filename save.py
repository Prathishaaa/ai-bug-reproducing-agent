# save.py - one job: write the result of one run to results/<bug>.json.
import json
import os


def save_result(result):
    os.makedirs("results", exist_ok=True)
    path = os.path.join("results", result["bug"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return path
