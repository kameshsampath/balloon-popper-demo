# Streaming Analytics Demo with Risingwave, Apache Iceberg and Apache Polaris.

[![Build Polaris Admin Tool PostgreSQL](https://github.com/Snowflake-Labs/polaris-local-forge/actions/workflows/polaris-admin-tool.yml/badge.svg)](https://github.com/Snowflake-Labs/polaris-local-forge/actions/workflows/polaris-admin-tool.yml)
[![Build PolarisServer with PostgreSQL](https://github.com/Snowflake-Labs/polaris-local-forge/actions/workflows/polaris-server-image.yml/badge.svg)](https://github.com/Snowflake-Labs/polaris-local-forge/actions/workflows/polaris-server-image.yml)
![k3d](https://img.shields.io/badge/k3d-v5.6.0-427cc9)
![Docker Desktop](https://img.shields.io/badge/Docker%20Desktop-v4.27-0db7ed)
![Apache Polaris](https://img.shields.io/badge/Apache%20Polaris-1.0.0--SNAPSHOT-f9a825)
![LocalStack](https://img.shields.io/badge/LocalStack-3.0.0-46a831)

This demo showcases streaming analytics using RisingWave with Apache Iceberg integration, visualized through a Streamlit dashboard. It processes real-time data from a balloon popping game, demonstrating RisingWave's stream processing capabilities connected to Apache Iceberg for data lake storage. The demo features live game metrics, materialized views, and shows how to implement end-to-end stream processing workflows with interactive visualizations.

Key features:

- Real-time game metrics processing with RisingWave
- Durable storage with Apache Iceberg data lake
- Interactive Streamlit dashboard for game analytics
- Apache Polaris REST Catalog with LocalStack S3 integration
- Materialized views for instant query responses
- Stream processing pipelines for game events

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Docker Engine](https://docs.docker.com/engine/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) - Kubernetes command-line tool
- [rpk](https://docs.redpanda.com/current/get-started/rpk-install/) - RPK CLI to interact with Apache Kafka cluster
- [k3d](https://k3d.io/) (>= 5.0.0) - Lightweight wrapper to run [k3s](https://k3s.io) in Docker
- [Python](https://www.python.org/downloads/) >= 3.12
- [uv](https://github.com/astral-sh/uv) - Python packaging tool
- [Task](https://taskfile.dev) - Makefile in YAML
- [LocalStack](https://localstack.cloud/) (>= 3.0.0) - AWS cloud service emulator
- [Dnsmasq](https://dnsmasq.org/doc.html) - **Optional** to avoid editing `/etc/hosts`

> **Important**
> Ensure the tools are downloaded and on your path before proceeding further with this tutorial.

## Documentation

Check out the [HTML Documentation](https://kameshsampath.github.io/balloon-popper-demo) for detailed instructions on running this demo locally.

## Cleanup

Cleanup the Polaris resources:

```bash
$PROJECT_HOME/polaris-forge-setup/catalog_cleanup.yml
```

Delete the whole cluster:

```bash
$PROJECT_HOME/bin/cleanup.sh
```

## Related Projects and Tools

### Core Components

- [Apache Polaris](https://github.com/apache/arrow-datafusion-python) - Data Catalog and Governance Platform
- [PyIceberg](https://py.iceberg.apache.org/) - Python library to interact with Apache Iceberg
- [Risingwave](https://docs.risingwave.com/) - Risingwave Streaming Database
- [LocalStack](https://github.com/localstack/localstack) - AWS Cloud Service Emulator
- [k3d](https://k3d.io) - k3s in Docker
- [k3s](https://k3s.io) - Lightweight Kubernetes Distribution

### Development Tools

- [Docker](https://www.docker.com/) - Container Platform
- [Kubernetes](https://kubernetes.io/) - Container Orchestration
- [Helm](https://helm.sh/) - Kubernetes Package Manager
- [kubectl](https://kubernetes.io/docs/reference/kubectl/) - Kubernetes CLI
- [uv](https://github.com/astral-sh/uv) - Python Packaging Tool

### Documentation

- [Ansible](https://docs.ansible.com/ansible/latest/getting_started/index.html)
- [Ansible Crypto Module](https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html)
- [Ansible AWS Module](https://docs.ansible.com/ansible/latest/collections/amazon/aws/index.html)
- [Ansible Kubernetes Module](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html)
- [k3d Documentation](https://k3d.io/v5.5.1/)
- [LocalStack Documentation](https://docs.localstack.cloud/overview/)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
- [Docker Documentation](https://docs.docker.com/)

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
