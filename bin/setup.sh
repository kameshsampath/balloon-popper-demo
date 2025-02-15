#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p "$(dirname "$KUBECONFIG")"

# Common platform detection
os=$(uname -s | tr '[:upper:]' '[:lower:]')
arch=$(uname -m)

# Arch mapping for kubectl (keeps x86_64)
kubectl_arch=$arch
case "$arch" in
    aarch64|arm64) kubectl_arch="arm64" ;;
esac

# Arch mapping for RPK (converts x86_64 to amd64)
rpk_arch=$arch
case "$arch" in
    x86_64) rpk_arch="amd64" ;;
    aarch64|arm64) rpk_arch="arm64" ;;
esac

# Download kubectl
curl -sSL "https://dl.k8s.io/release/${K3S_VERSION%[+-]*}/bin/${os}/${kubectl_arch}/kubectl" -o "$PWD/bin/kubectl"

# Download RPK
curl -sSL "https://github.com/redpanda-data/redpanda/releases/latest/download/rpk-${os}-${rpk_arch}.zip" -o rpk.zip && \
    unzip -o rpk.zip -d"$PWD/bin/" && \
    rm rpk.zip && \
    chmod +x "$PWD/bin/rpk"

k3d cluster create \
  --config="${SCRIPT_DIR}/../config/cluster-config.yaml"