# docker_run.py - one job: run test_bug.py inside the sealed box and return what it printed.
import os
import subprocess
import sys

# Inside the box: install the project (no internet needed), then run the test for 60 seconds at most.
INSIDE = (
    "pip install -q --root-user-action=ignore --no-deps --no-build-isolation -e . "
    "&& timeout 60 pytest -q --color=no --tb=short test_bug.py"
)


def run_test(folder):
    # "docker info" only works when Docker Desktop is open.
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        raise SystemExit("Docker is not running. Open Docker Desktop and try again.")
    command = [
        "docker", "run", "--rm",
        "--network", "none",                           # no internet
        "--memory", "512m",                            # 512 MB memory at most
        "-e", "SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0",  # lets projects install without git
        "-v", os.path.abspath(folder) + ":/app",       # the box sees only this folder
        "-w", "/app",
        "bug-box", "sh", "-c", INSIDE,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    return result.stdout + result.stderr


if __name__ == "__main__":
    # Try it: python docker_run.py L1
    print(run_test(os.path.join("workspace", sys.argv[1])))
