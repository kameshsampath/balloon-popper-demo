# Getting Started with Balloon Popper Game

## Learning Objectives

By the end of this chapter, you will:

- Install all required tools and dependencies
- Clone and configure the project repository
- Set up a Python virtual environment with necessary packages
- Understand the project structure
- Configure DNS settings for streamlined development (optional)

## Prerequisites

Before beginning this tutorial, ensure you have the following tools installed and properly configured:

| Tool | Purpose | Minimum Version | Remarks
|------|---------|----------------|----------------|
| [GitHub Account](https://github.com/signup){target=_blank} | Repository access | N/A |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/){target=_blank}  | Container runtime | Latest |
| [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl){target=_blank}  | Kubernetes CLI | Latest | `$PROJECT_HOME/setup.sh` will download latest matching the cluster version
| [rpk](https://docs.redpanda.com/current/get-started/rpk-install/){target=_blank}  | Kafka CLI | Latest | `$PROJECT_HOME/setup.sh` will download latest matching the cluster Kafka version
| [k3d](https://k3d.io/){target=_blank}  | Lightweight Kubernetes | >= 5.0.0 |
| [Python](https://www.python.org/downloads/){target=_blank}  | Programming language | >= 3.12 |
| [psql](https://wiki.postgresql.org/wiki/PostgreSQL_Clients#psql){target=_blank}  | PostgreSQL CLI Client | >= 17.4 | PostgreSQL client to work with Risingwave using SQL
| [uv](https://github.com/astral-sh/uv){target=_blank}  | Python package manager | Latest |
| [Task](https://taskfile.dev){target=_blank}  | Task runner | Latest |
| [LocalStack](https://localstack.cloud/){target=_blank}  | AWS emulator | >= 3.0.0 |
| [Dnsmasq](https://dnsmasq.org/doc.html){target=_blank}  | DNS management | Latest (Optional) |

!!! warning "Prerequisites Check"
    Make sure all required tools are properly installed and available in your system PATH before proceeding. This will prevent issues later in the setup process.

## Setting Up the Project

### Step 1: Clone the Repository

```bash
git clone https://github.com/kameshsampath/balloon-popper-game
cd balloon-popper-game
```

### Step 2: Configure Environment Variables

Set up essential environment variables for the project:

```bash
export PROJECT_HOME="$PWD"
export KUBECONFIG="$PWD/.kube/config"
export K3D_CLUSTER_NAME=balloon-popper-demo
export K3S_VERSION=v1.32.1-k3s1
export FEATURES_DIR="$PWD/k8s"
```

!!! tip "Environment Management"
    Consider using [direnv](https://direnv.net){target=_blank}  to automatically set environment variables when entering the project directory. This simplifies your workflow and ensures consistent configuration.

### Step 3: Set Up Python Environment

Create and activate a Python virtual environment:

```bash
# Pin Python version
uv python pin 3.12

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/Linux/macOS
# OR
.venv\Scripts\activate     # On Windows

# Install dependencies
uv sync
```

!!! note
    The virtual environment isolates your project dependencies from system-wide Python packages, preventing conflicts and ensuring reproducibility.

### Step 4: DNS Configuration

For seamless access to services within your local Kubernetes cluster.

On macOS with Homebrew:

```bash
# Configure Dnsmasq to resolve .localstack domains to localhost
echo "address=/.localstack/127.0.0.1" >> $(brew --prefix)/etc/dnsmasq.conf

# Configure macOS to use Dnsmasq for .localstack domains
sudo mkdir -p /etc/resolver
cat <<EOF | sudo tee /etc/resolver/localstack
nameserver 127.0.0.1
EOF
```

!!! info
    After configuring Dnsmasq, you may need to restart the service and flush your DNS cache for changes to take effect.

(OR)

Edit `/etc/hosts` and add the following entry

```shell
127.0.0.1 *.localstack
```

## Project Structure Overview

The repository is organized into several key directories:

- `bin/`: Contains setup and cleanup scripts
- `config/`: Kubernetes cluster configuration
- `k8s/`: Kubernetes manifests for all components
  - `features/`: Core infrastructure components (Kafka, LocalStack, etc.)
  - `generator/`: Event generator deployment
  - `polaris/`: Apache Polaris configuration
- `notebooks/`: Jupyter notebooks for analysis
- `packages/`: Python packages for the application components
  - `common/`: Shared utilities
  - `dashboard/`: Streamlit dashboard
  - `generator/`: Event generation logic
- `polaris-forge-setup/`: Ansible playbooks for infrastructure setup
- `scripts/`: Generated SQL scripts (will be created in later steps)
- `work/`: Working directory for credentials and temporary files

!!! note "Generated Files"
    Several configuration files containing sensitive information are not included in the repository and will be generated during the setup process:
    
    - `k8s/features/postgresql.yaml`
    - `k8s/features/risingwave.yaml`
    - `k8s/polaris/persistence.xml`
    - `k8s/polaris/.bootstrap-credentials`
    - `k8s/polaris/.polaris.env`
    - RSA key pairs
    - SQL scripts

## Next Steps

Now that you have set up the project environment, you're ready to create your local Kubernetes cluster and deploy the necessary components. In the next chapter, we'll set up the local cloud infrastructure using K3d and deploy essential services like Kafka, LocalStack, and Apache Polaris.

!!! success "Checkpoint"
    Before proceeding to the next chapter, ensure that:
    
    - All required tools are installed
    - The repository is cloned and environment variables are set
    - The Python virtual environment is activated
    - You understand the basic project structure