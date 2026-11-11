# test_check.py - tests for the judge, using 4 real outputs saved from the sealed box.
from check import is_match


def read(name):
    with open(f"data/outputs/{name}.txt", encoding="utf-8") as f:
        return f.read()


def test_real_match():
    # The test reached humanize's code and hit the reported error.
    assert is_match(read("match"), "OverflowError")


def test_wrong_error():
    # It failed in humanize's code, but with ValueError, not OverflowError.
    assert not is_match(read("wrong_error"), "OverflowError")


def test_broken_test():
    # The test had a typo, so it could not even start.
    assert not is_match(read("broken"), "OverflowError")


def test_cheating_test():
    # The test raised OverflowError itself and never used humanize.
    assert not is_match(read("cheating"), "OverflowError")
