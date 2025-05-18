#!/usr/bin/env bash
# This script sets up the environment for the project.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PROJECT_HOME="$(cd "${SCRIPT_DIR}/.." && pwd)"
export KUBECONFIG="${PROJECT_HOME}/.kube/config"
export K3D_CLUSTER_NAME="balloon-popper-demo"
export K3S_VERSION="v1.32.1-k3s1"
export FEATURES_DIR="${PROJECT_HOME}/k8s"
export PGHOST=localhost
export PGPORT=14567
export PGDATABASE=dev
export PGUSER=root
export PGPASSWORD=
export AWS_ENDPOINT_URL=http://localstack.localstack:4566 
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
export CATALOG_NAME="balloon-game"
export CATALOG_NAMESPACE="game_events"
export ICEBERG_REST_URI=http://localhost:18181/api/catalog
export KAFKA_BOOTSTRAP_SERVERS=localhost:19094
export RPK_BROKERS=localhost:19094

# Setup Python virtual environment
# Ensure we are using the correct Python version
uv python pin 3.12
# Create a virtual environment
if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment..."
  uv venv
else
  echo "Virtual environment already exists."
fi
# activate the virtual environment
if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Error: Virtual environment not found!"
  exit 1
fi
echo "Activating virtual environment..."
# shellcheck disable=SC1090
source .venv/bin/activate
# Install dependencies
uv sync

# Ensure we are in the right venv
if [[ "$VIRTUAL_ENV" != "$PWD/.venv" ]]; then
  echo "Error: Not in the expected virtual environment!"
  exit 1
fi
echo "Activated virtual environment: $VIRTUAL_ENV"

# Install dnsmmasq and configure it
if ! command -v brew &> /dev/null; then
  echo "Homebrew not found. Please install Homebrew first."
  exit 1
fi
if ! command -v dnsmasq &> /dev/null; then
  echo "Installing dnsmasq..."
  brew install dnsmasq
else
  echo "dnsmasq is already installed."
fi
# Configure Dnsmasq to resolve .localstack domains to localhost
if ! grep -q "address=/.localstack/127.0.0.1" "$(brew --prefix)/etc/dnsmasq.conf"; then
  echo "address=/.localstack/127.0.0.1" >> "$(brew --prefix)/etc/dnsmasq.conf"
  echo "Added .localstack configuration to dnsmasq.conf"
else
  echo ".localstack configuration already exists in dnsmasq.conf"
fi

# Configure macOS to use Dnsmasq for .localstack domains
if [[ ! -d "/etc/resolver" ]]; then
  sudo mkdir -p /etc/resolver
fi
if [[ ! -f "/etc/resolver/localstack" ]]; then
  cat <<EOF | sudo tee /etc/resolver/localstack
nameserver 127.0.0.1
EOF
  echo "Created /etc/resolver/localstack configuration"
else
  echo "/etc/resolver/localstack configuration already exists"
fi

# Start/Restart dnsmasq
if ! pgrep -x "dnsmasq" > /dev/null; then
  echo "Starting dnsmasq..."
  brew services restart dnsmasq
else
  echo "dnsmasq is already running."
fi

# Check if k3d is installed
if ! command -v k3d &> /dev/null; then
  echo "Installing k3d..."
  brew install k3d
else
  echo "k3d is already installed."
fi

# Check if the k3d cluster exists
if ! k3d cluster get "$K3D_CLUSTER_NAME" &> /dev/null; then
  echo "Creating new k3d cluster..."
  # Generate the required manifests for setting up the kubernetes cluster
  ansible-playbook $PROJECT_HOME/polaris-forge-setup/prepare.yml

  # Setup Demo components
  $PROJECT_HOME/bin/setup.sh
else
  echo "K3d cluster '$K3D_CLUSTER_NAME' already exists."
fi

# Wait for components to be ready
ansible-playbook $PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags=bootstrap

# Deploy Apache Polaris(Incubating) to the cluster
kubectl apply -k $PROJECT_HOME/k8s/polaris

# Wait for polaris to be ready
ansible-playbook $PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags=polaris

# Setup Apache Iceberg Catalog using Apache Polaris(Incubating)
ansible-playbook $PROJECT_HOME/polaris-forge-setup/catalog_setup.yml

# Create the required Apache Iceberg namespaces, tables etc.,
python "$SCRIPT_DIR/create_tables.py"

# Create Sources and Sinks
ansible-playbook $PROJECT_HOME/polaris-forge-setup/generate_source_sinks.yml

# Create RisingWave Sources and Sinks
psql -f $PROJECT_HOME/scripts/source.sql
psql -f $PROJECT_HOME/scripts/sink.sql

# Print out all the sources and sinks
echo "Sources and Sinks created:"
psql -c "SHOW SOURCES;"
psql -c "SHOW MATERIALIZED VIEWS;"
psql -c "SHOW SINKS;"