# docker_run.py - one job: run a test inside the sealed box and return what it printed.
import os
import subprocess
import sys

PIP = "pip install -q --root-user-action=ignore"
# Install the project and its test packages. Unknown extras like [tests] are just skipped.
# Then install test packages listed in other files or groups. If one of those fails, keep going.
INSTALL = (
    f"{PIP} -e .[test,tests,testing] || exit 1; "
    f"for f in requirements/test*.txt requirements-test*.txt test-requirements.txt requirements/dev.txt; "
    f"do [ -f $f ] && {PIP} -r $f; done; "
    f"for g in test tests dev; do {PIP} --group $g 2>/dev/null; done; "
    f"{PIP} -U pytest; exit 0"  # those lists can bring an old pytest that breaks on Python 3.12
)


def check_docker():
    # "docker info" only works when Docker Desktop is open.
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        raise SystemExit("Docker is not running. Open Docker Desktop and try again.")


def prepare_box(folder, bug_id):
    # Set up a room for this bug once, WITH internet, then save it as a snapshot.
    image = "bug-box-" + bug_id.lower()
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0:
        return image  # already set up
    check_docker()
    name = image + "-setup"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    mount = ["-v", os.path.abspath(folder) + ":/app", "-w", "/app"]
    setup = subprocess.run(["docker", "run", "--name", name, *mount, "bug-box", "sh", "-c", INSTALL])
    if setup.returncode != 0:
        subprocess.run(["docker", "rm", name], capture_output=True)
        raise RuntimeError("Could not set up this project in the room (pip install failed).")
    subprocess.run(["docker", "commit", name, image], check=True, capture_output=True)
    subprocess.run(["docker", "rm", name], capture_output=True)
    return image


def run_test(folder, bug_id, test_file="test_bug.py"):
    # Run the test in the snapshot WITHOUT internet, with 512 MB memory and 60 seconds at most.
    check_docker()
    command = [
        "docker", "run", "--rm", "--network", "none", "--memory", "512m",
        "-v", os.path.abspath(folder) + ":/app", "-w", "/app",
        prepare_box(folder, bug_id),
        "timeout", "60", "pytest", "-q", "--color=no", "--tb=short", "-p", "no:cacheprovider", test_file,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    return result.stdout + result.stderr


if __name__ == "__main__":
    # Try it: python docker_run.py L1
    bug_id = sys.argv[1]
    print(run_test(os.path.join("workspace", bug_id), bug_id))
