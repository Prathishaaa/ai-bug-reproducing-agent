# Dockerfile - the recipe for the sealed box. Build it once: docker build -t bug-box .
FROM python:3.12-slim
# git lets projects read their own version. gcc builds projects that have C code.
RUN apt-get update && apt-get install -y --no-install-recommends git gcc libc6-dev && rm -rf /var/lib/apt/lists/* \
    && git config --global --add safe.directory "*"
# pytest runs the tests. pytest-timeout stops a frozen test and shows the line it was stuck on.
# The rest are build tools that projects need to install themselves.
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir pytest pytest-timeout hatchling hatch-vcs \
    setuptools setuptools-scm flit-core poetry-core editables
