# Setup

In this chapter, we will guide you through the following steps:

- Setting tools needed for running this tutorial
- Cloning the demo sources to your local machine
- Configuring the project settings
- Optionally Running the starter app locally to ensure everything is set up correctly

Let's get started!

## What is required

To follow along with this tutorial and set up your project successfully, you'll need the following tools and accounts:

- A [GitHub account](https://github.com/signup){:target=\_blank}: If you don't already have a GitHub account, you'll need to create one.

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Docker Engine](https://docs.docker.com/engine/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) - Kubernetes command-line tool
- [rpk](https://docs.redpanda.com/current/get-started/rpk-install/) - RPK CLI to interact with Apache Kafka cluster
- [k3d](https://k3d.io/) (>= 5.0.0) - Lightweight wrapper to run [k3s](https://k3s.io) in Docker
- [Python](https://www.python.org/downloads/) >= 3.12
- [uv](https://github.com/astral-sh/uv) - Python packaging tool
- [Task](https://taskfile.dev) - Makefile in YAML
- [LocalStack](https://localstack.cloud/) (>= 3.0.0) - AWS cloud service emulator
- [Dnsmasq](https://dnsmasq.org/doc.html) - **Optional** to avoid editing `/etc/hosts`

!!!Important
    Ensure the tools are downloaded and on your path before proceeding further with this tutorial.

## Get the Sources

Clone the repository:

```bash
git clone https://github.com/kameshsampath/balloon-popper-game
cd balloon-popper-game
```

Set up environment variables:

```bash
export PROJECT_HOME="$PWD"
export KUBECONFIG="$PWD/.kube/config"
export K3D_CLUSTER_NAME=balloon-popper-demo
export K3S_VERSION=v1.32.1-k3s1
export FEATURES_DIR="$PWD/k8s"
```

!!!TIP
     Use tools like [direnv](https://direnv.net) to make it easy setting environment variables

Going forward we will refer to the cloned sources folder as `$PROJECT_HOME`.

## Python Virtual Environment

Let us setup Python virtual environment and required tools.

```bash
# Pin python version
uv python pin 3.12
# Install and set up Python environment
uv venv
# On Unix-like systems
source .venv/bin/activate
# Install deps/packages.old
uv sync
```


## DNSmasq

For seamless access of services with the local k3s cluster and host, we might need to add entries in `/etc/hosts` of the host. But using dnsmasq is a much cleaner and neater way.

Assuming you have `dnsmasq` installed, here is what is needed to set that up on macOS:

```shell
echo "address=/.localstack/127.0.0.1" >> $(brew --prefix)/etc/dnsmasq.conf
```

```shell
cat <<EOF | sudo tee /etc/resolver/localstack
nameserver 127.0.0.1
EOF
```

## Directory Structure

The project has the following directories and files:

```text
.
├── LICENSE
├── README.md
├── Taskfile.yml
├── bin
│   ├── cleanup.sh
│   └── setup.sh
├── config
│   └── cluster-config.yaml
├── docs
│   ├── catalog_data.png
│   ├── catalog_metadata.png
│   ├── catalog_storage.png
│   └── localstack_view.png
├── k8s
│   ├── features
│   │   ├── adminer.yaml
│   │   ├── cert-manager.yaml
│   │   ├── kafka-cluster.yaml
│   │   ├── localstack.yaml
│   │   └── strimzi-kafka-op.yaml
│   ├── generator
│   │   ├── deployment.yaml
│   │   └── kustomization.yaml
│   └── polaris
│       ├── deployment.yaml
│       ├── jobs
│       │   ├── job-bootstrap.yaml
│       │   ├── job-purge.yaml
│       │   └── kustomization.yaml
│       ├── kustomization.yaml
│       ├── rbac.yaml
│       ├── sa.yaml
│       └── service.yaml
├── notebooks
│   └── workbook.ipynb
├── packages
│   ├── common
│   │   ├── README.md
│   │   ├── pyproject.toml
│   │   └── src
│   │       └── common
│   │           ├── __init__.py
│   │           ├── log
│   │           │   ├── __init__.py
│   │           │   └── logger.py
│   │           └── py.typed
│   ├── dashboard
│   │   ├── README.md
│   │   ├── pyproject.toml
│   │   └── src
│   │       └── dashboard
│   │           ├── __init__.py
│   │           └── streamlit_app.py
│   └── generator
│       ├── Dockerfile
│       ├── README.md
│       ├── pyproject.toml
│       └── src
│           ├── generator
│           │   └── __init__.py
│           └── stream
│               ├── __init__.py
│               ├── balloon_popper.py
│               └── models.py
├── polaris-forge-setup
│   ├── ansible.cfg
│   ├── catalog_cleanup.yml
│   ├── catalog_setup.yml
│   ├── cluster_checks.yml
│   ├── defaults
│   │   └── main.yml
│   ├── generate_source_sinks.yml
│   ├── inventory
│   │   └── hosts
│   ├── prepare.yml
│   ├── tasks
│   │   ├── drop_tables.yml
│   │   ├── kafka_checks.yml
│   │   ├── localstack_checks.yml
│   │   ├── polaris_checks.yml
│   │   └── risingwave_checks.yml
│   └── templates
│       ├── bootstrap-credentials.env.j2
│       ├── persistence.xml.j2
│       ├── polaris.env.j2
│       ├── postgresql.yml.j2
│       ├── risingwave.yaml.j2
│       ├── sink.sql.j2
│       └── source.sql.j2
├── pyproject.toml
├── scripts
├── uv.lock
└── work
```

!!!NOTE
    To ensure reuse and for security, files with passwords are not added to git. Currently, the following files are ignored or not available out of the box (they will be generated in upcoming steps):

    - k8s/features/postgresql.yaml
    - k8s/features/risingwave.yaml
    - k8s/polaris/persistence.xml
    - k8s/polaris/.bootstrap-credentials
    - k8s/polaris/.polaris.env
    - All RSA KeyPairs
    - scripts/\*.sql
