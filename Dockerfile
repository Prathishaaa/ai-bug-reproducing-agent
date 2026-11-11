# Dockerfile - the recipe for the sealed box. Build it once: docker build -t bug-box .
FROM python:3.12-slim
# pytest runs the tests. The rest are build tools that projects need to install themselves.
RUN pip install --no-cache-dir pytest hatchling hatch-vcs setuptools setuptools-scm flit-core poetry-core editables
