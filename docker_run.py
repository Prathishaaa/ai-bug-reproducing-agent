# docker_run.py - one job: run a test inside the sealed box and return what it printed.
import csv
import os
import subprocess
import sys


def install_command(date, extra_packages=""):
    # With a date, pip installs packages as they were on that day, so new versions cannot break old code.
    pip = "pip install -q --root-user-action=ignore"
    dated = f"{pip} --uploaded-prior-to={date}T00:00:00Z" if date else pip
    # 1. The project and its test packages. Unknown extras like [tests] are just skipped.
    steps = f"{dated} -e .[test,tests,testing] || exit 1; "
    # 2. Packages the project needs but forgot to list (extra_packages in bugs.csv).
    if extra_packages:
        steps += f"{dated} {extra_packages}; "
    # 3. Test packages listed in other files or groups. If one of those fails, keep going.
    steps += "for f in requirements/test*.txt requirements-test*.txt test-requirements.txt requirements/dev.txt; "
    steps += f"do [ -f $f ] && {dated} -r $f; done; "
    steps += f"for g in test tests dev; do {dated} --group $g 2>/dev/null; done; "
    # 4. Always today's pytest: old ones break on Python 3.12.
    steps += f"{pip} -U pytest pytest-timeout; exit 0"
    return steps


def check_docker():
    # "docker info" only works when Docker Desktop is open.
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        raise SystemExit("Docker is not running. Open Docker Desktop and try again.")


def bug_settings(bug_id):
    # Extra needs from data/bugs.csv: packages the project forgot to list, and settings its tests read.
    with open("data/bugs.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] == bug_id:
                return row.get("extra_packages", ""), row.get("test_env", "")
    return "", ""  # a GitHub link, not from our list


def prepare_box(folder, bug_id, date=""):
    # Set up a room for this bug once, WITH internet, then save it as a snapshot.
    image = "bug-box-" + bug_id.lower()
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0:
        return image  # already set up
    check_docker()
    name = image + "-setup"
    mount = ["-v", os.path.abspath(folder) + ":/app", "-w", "/app"]
    extra_packages, _ = bug_settings(bug_id)
    # Try packages from the bug's date first. If that fails (too old for Python 3.12), use today's.
    for install_date in ([date, ""] if date else [""]):
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        setup = subprocess.run(["docker", "run", "--name", name, *mount, "bug-box", "sh", "-c",
                                install_command(install_date, extra_packages)])
        if setup.returncode == 0:
            break
    if setup.returncode != 0:
        subprocess.run(["docker", "rm", name], capture_output=True)
        raise RuntimeError("Could not set up this project in the room (pip install failed).")
    subprocess.run(["docker", "commit", name, image], check=True, capture_output=True)
    subprocess.run(["docker", "rm", name], capture_output=True)
    return image


def run_test(folder, bug_id, test_args=("test_bug.py",)):
    # Run the test in the snapshot WITHOUT internet, with 512 MB memory and 60 seconds at most.
    check_docker()
    _, test_env = bug_settings(bug_id)
    env = [part for setting in test_env.split(";") if setting for part in ("-e", setting)]
    command = [
        "docker", "run", "--rm", "--network", "none", "--memory", "512m", *env,
        "-v", os.path.abspath(folder) + ":/app", "-w", "/app",
        prepare_box(folder, bug_id),
        # --timeout=20 stops a frozen test after 20 seconds and shows where it was stuck.
        # The outer "timeout 60" is a backup in case even that does not work.
        "timeout", "60", "pytest", "-q", "--color=no", "--tb=short", "-p", "no:cacheprovider",
        "--timeout=20", *test_args,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    return result.stdout + result.stderr


if __name__ == "__main__":
    # Try it: python docker_run.py L1
    bug_id = sys.argv[1]
    print(run_test(os.path.join("workspace", bug_id), bug_id))
