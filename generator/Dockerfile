# syntax=docker/dockerfile:1

FROM cgr.dev/chainguard/python:latest-dev AS dev

WORKDIR /app

ADD . .
RUN uv venv
ENV PATH="/app/.venv/bin:$PATH"

# COPY requirements.txt requirements.txt
# RUN pip install -r requirements.txt
RUN source activate .venv/bin/activate \
  && uv sync  --no-cache --no-sources --verbose

FROM cgr.dev/chainguard/python

WORKDIR /app

COPY *.py .
COPY --from=dev /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "balloon_popper.py"]