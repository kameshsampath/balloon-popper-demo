# Balloon popper → Snowflake lakehouse lab (in progress)

This repository is **transitioning** from the original **RisingWave + k3d + Polaris** streaming demo to a **Snowflake** quickstart-style lab (**Iceberg**, catalog-linked bronze, **Dynamic Iceberg Tables**, **Streamlit in Snowflake**). The supported path is **AWS Glue** bronze on S3, **Snowflake** for catalog / CLD / DTs, and **DuckDB** only where the guide calls for local read-only checks. Legacy trees (`k8s/`, `polaris-forge-setup/`, `docs/`, `mkdocs.yaml`) remain **for now** so [sfguides/EXTRACTION_MAP.md](sfguides/EXTRACTION_MAP.md) and [snowflake/lab/REFERENCE.md](snowflake/lab/REFERENCE.md) can keep pointing at them until the **companion-repo-delete** phase.

## Where to start (new lab path)

| Area | Link |
|------|------|
| Bronze (AWS, Glue, S3 Tables, sample load) | [lab/bronze-landing-zone.md](lab/bronze-landing-zone.md), [tools/bronze_preload/README.md](tools/bronze_preload/README.md), [manual test plan](lab/bronze-landing-zone-MANUAL-TEST.md) |
| Env template (Phase 0) | [`.env.example`](.env.example) |
| Snowflake SQL (scaffold) | [snowflake/lab/](snowflake/lab/) |
| SFGuide extraction | [sfguides/EXTRACTION_MAP.md](sfguides/EXTRACTION_MAP.md) |
| Plan | [plans/snowflake_stack_refactor_97a1b8ee.plan.md](plans/snowflake_stack_refactor_97a1b8ee.plan.md) |

**Prerequisites (Snowflake / bronze track):** Python **3.12+**; CLIs **`aws`**, **`snow`**, **`task`**, **`envsubst`** (gettext), **`jq`**, **[Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli)** (`cortex`), and **[uv](https://github.com/astral-sh/uv)**. **Recommended:** **[direnv](https://direnv.net/)** (matches this repo’s [`.envrc`](.envrc)), **`curl`**, and **`openssl`**. AWS CLI **2.34+** for `aws s3tables`. Configure **`AWS_PROFILE`** (see `.env.example`). From the repo root run **`task check-tools`** to verify everything is on your `PATH` (Windows, Linux, macOS).

## Legacy demo (deprecated)

The sections below describe the **old** k3d / RisingWave / MkDocs flow. The root **Taskfile** no longer defines **kubectl** / **docker** cluster tasks (Glue + Snowflake + DuckDB is the supported path). GitHub Pages **docs workflow** and **cluster `bin/*.sh` helpers** have been removed; do not rely on `bin/cleanup.sh`.

- **HTML docs** — the MkDocs publish workflow was removed; use markdown under [`docs/`](docs/) locally until content is migrated.
- **Polaris cleanup** — if you still run Ansible from `polaris-forge-setup/`, use `ansible-playbook` with the playbooks there (see that folder’s README if present).

## Related projects

- [Apache Iceberg](https://iceberg.apache.org/), [PyIceberg](https://py.iceberg.apache.org/)
- [Snowflake + Glue S3 Tables gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) (catalog integration patterns)

## License

Copyright (c) Kamesh Sampath. All rights reserved. Licensed under the Apache 2.0 license.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
