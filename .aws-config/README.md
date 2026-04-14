# Local AWS lab config (generated)

This directory holds **machine-local** artifacts for the bronze landing path: rendered IAM policy JSON, trust-policy snippets, optional `aws` CLI output you save for debugging, etc.

- Use **`AWS_PROFILE`** (and **`AWS_REGION`**) with the real AWS account; scripts should write here at **runtime**, not commit filled files.
- Everything except this `README` and any `*.example` files is **gitignored**—do not paste secrets into the repo.

Templates live under **`lab/aws/`** (or similar) once the bronze automation is added.
