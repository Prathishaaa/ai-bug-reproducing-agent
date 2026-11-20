# AI Bug Reproducing Agent

An AI agent that reads a GitHub bug report and writes a **pytest test that shows the bug**. It runs the test in a sealed Docker container with no internet, and then checks the test against the developers' real fix.

**Result: 53 of 99 real GitHub bugs reproduced (54%)**, and every one of those tests was confirmed with the real fix. The median time per reproduced bug was about 52 seconds, using only a free Gemini model.

## Why

Before a bug can be fixed, someone has to reproduce it, which means writing a small test that fails because of the bug. This is slow, manual work. This project tries to do that step automatically, starting from nothing but the bug report.

## How it works

1. **Read the bug.** Gemini reads the issue and names the error it expects (for example `OverflowError`) plus a few words to search the code for.
2. **Pick the code.** Python scores the project's files and keeps the 3 most related ones.
3. **Write a test.** Gemini guesses the cause and writes `test_bug.py`.
4. **Run it in a sealed box.** The test runs in Docker with no network, a memory limit, and a timeout, so code written by the AI can't do harm.
5. **Judge it in Python, not with AI.** The test only counts if it failed, failed with the same error as the report, and failed inside the project's own code.
6. **Retry with feedback.** If the judge says no, Gemini is told why and tries again, up to 4 times.
7. **Check against the real fix.** The same test is run on the developers' fixed code. A real reproduction must **pass** there.

## Results

The test set is 99 real, already-fixed bugs from public Python projects. Each one was checked beforehand: the developers' own tests fail before their fix and pass after it.

- **Reproduced and confirmed with the real fix: 53 of 99 (54%)**
- 47 worked on the first try, and the retry loop added 6 more.
- By type: database 13 of 16, logic 32 of 64, API 7 of 17, freeze 1 of 2.
- Median time for a reproduced bug: about 52 seconds.

**Why the real-fix check matters:** the Python judge said yes 76 times, but only 53 of those tests passed on the real fix. The other 23 still failed after the fix, so they weren't really showing this bug. Without the final check, the score would have looked like 77%, so only the confirmed 53 are counted.

Full per-bug results are in [`results/summary.csv`](results/summary.csv), with one JSON file per bug in `results/`.

## Run it yourself

You need Python 3.12, Docker, and a free Gemini API key from [Google AI Studio](https://aistudio.google.com).

```
pip install -r requirements.txt
docker build -t bug-box .
```

Copy `.env.example` to `.env` and fill in your own key. Never commit `.env`.

```
python agent.py L1                                          # one bug from data/bugs.csv
python agent.py https://github.com/owner/repo/issues/123    # or any GitHub issue link
python evaluate.py                                          # run every bug and write results/summary.csv
```

## Files

Each file has one job.

- `agent.py` runs all the steps for one bug.
- `download.py` gets the project code (before the fix) and the bug report.
- `pick_files.py` finds the files most related to the bug.
- `prompts.py` and `llm.py` hold the questions for Gemini and send them.
- `docker_run.py` runs a test inside the sealed container.
- `check.py` is the Python judge, and `test_check.py` tests it.
- `verify.py` checks a test against the developers' real fix.
- `evaluate.py` runs the full test set.
- `find_bugs.py` finds fixed bugs on GitHub to add to `data/bugs.csv`.

## Limits

- API bugs were the hardest (7 of 17). These often need a mocked server or exact setup that is hard to guess from the report alone.
- Python projects only.
- The real-fix check is used only for scoring. In real use there is no fix yet, so the Python judge is the only check.
