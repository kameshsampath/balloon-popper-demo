# Balloon popper → Snowflake lakehouse lab

Hands-on lab for **Apache Iceberg** on **AWS** (Glue, S3, optional S3 Tables) and **Snowflake**: catalog-linked bronze, **Dynamic Iceberg Tables**, and **Streamlit in Snowflake**. **DuckDB** appears only where the guide calls for optional local read-only checks. Work from the repo root with **`uv`**, **`task`**, and **`task check-tools`**.

## Where to start (new lab path)

| Area | Link |
|------|------|
| Bronze (AWS, Glue, S3 Tables, sample load) | [lab/bronze-landing-zone.md](lab/bronze-landing-zone.md), [tools/bronze_preload/README.md](tools/bronze_preload/README.md), [manual test plan](lab/bronze-landing-zone-MANUAL-TEST.md) |
| Snowflake CLD (catalog integration + linked DB) | [lab/snowflake-catalog-cld.md](lab/snowflake-catalog-cld.md), [manual test plan](lab/snowflake-cld-MANUAL-TEST.md), [snowflake/lab/](snowflake/lab/) |
| Snowflake Dynamic Iceberg Tables (silver) | [lab/snowflake-dynamic-iceberg-tables.md](lab/snowflake-dynamic-iceberg-tables.md), [manual test plan](lab/snowflake-dt-MANUAL-TEST.md), [snowflake/lab/REFERENCE.md](snowflake/lab/REFERENCE.md) |
| Streamlit in Snowflake (SiS) | [lab/snowflake-streamlit-sis.md](lab/snowflake-streamlit-sis.md), [snowflake/sis/](snowflake/sis/) (`snowflake.yml` + **`task snowflake:sis-deploy`**) |
| Env template (Phase 0) | [`.env.example`](.env.example) |
| Snowflake SQL + catalog trust / IAM | [snowflake/lab/README.md](snowflake/lab/README.md) — `task snowflake:*` (catalog + CLD), **`task dt:*`** (silver DT SQL); includes **`create-glue-catalog-read-role`**, **`apply-glue-catalog-trust-from-rendered`** |
| SFGuide extraction | [sfguides/EXTRACTION_MAP.md](sfguides/EXTRACTION_MAP.md) |
| Plan | [plans/snowflake_stack_refactor_97a1b8ee.plan.md](plans/snowflake_stack_refactor_97a1b8ee.plan.md) |

**Prerequisites (Snowflake / bronze track):** Python **3.12+**; CLIs **`aws`**, **`snow`**, **`task`**, **`envsubst`** (gettext), **`jq`**, **[Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli)** (`cortex`), and **[uv](https://github.com/astral-sh/uv)**. **Recommended:** **[direnv](https://direnv.net/)** (matches this repo’s [`.envrc`](.envrc)), **`curl`**, and **`openssl`**. AWS CLI **2.34+** for `aws s3tables`. Configure **`AWS_PROFILE`** (and **`AWS_REGION`**) with a **working session**—see `.env.example`. From the repo root run **`task check-tools`**: it verifies binaries on `PATH` and runs **`aws sts get-caller-identity`** so invalid or expired tokens fail fast before bronze tasks (Windows, Linux, macOS).

**OS install paths:** see the **“Install paths by OS”** table in [`sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md`](sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md) (macOS Homebrew, apt/dnf, Windows Scoop/Chocolatey/WSL2 for `envsubst`).

## Related projects

- [Apache Iceberg](https://iceberg.apache.org/), [PyIceberg](https://py.iceberg.apache.org/)
- [Snowflake + Glue S3 Tables gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) (catalog integration patterns)

## License

Copyright (c) Kamesh Sampath. All rights reserved. Licensed under the Apache 2.0 license.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
