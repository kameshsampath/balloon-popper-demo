# Local Cloud Setup

## Learning Objectives

By the end of this chapter, you will:

- Set up a local Kubernetes cluster for development
- Deploy essential cloud services including LocalStack, Kafka, and Apache Polaris
- Configure all components for the balloon game analytics pipeline
- Verify your installation to ensure everything is working correctly

## Configuration Overview

All configuration settings are managed through a single file: [defaults/main.yml](../polaris-forge-setup/defaults/main.yml)

!!! tip "Configuration Customization"
    The table below shows the key configuration parameters. You can adjust these values in the defaults file before deployment if needed.

| Name | Description | Default Value |
|------|------------|---------------|
| `plf_catalog_name` | Name of the Polaris catalog | `balloon-game` |
| `plf_admin_username` | Superuser for Polaris | `super_user` |
| `plf_admin_role` | Admin role name | `admin` |
| `plf_catalog_role` | Catalog role name | `sudo` |
| `balloon_game_db` | Iceberg database name | `balloon_pops` |
| `balloon_game_kafka_topic` | Kafka topic for game events | `balloon-game` |

!!! note
    For a complete list of configuration parameters, refer to the [defaults/main.yml](../polaris-forge-setup/defaults/main.yml) file.

## Deployment Process

### Step 1: Prepare Resources

First, generate the required configuration files and secrets:

```shell
ansible-playbook $PROJECT_HOME/polaris-forge-setup/prepare.yml
```

This playbook:
- Creates necessary directories
- Generates credential files
- Prepares Kubernetes manifests from templates

### Step 2: Create the Kubernetes Cluster

Run the cluster setup script:

```shell
$PROJECT_HOME/bin/setup.sh
```

This script:
- Creates a K3d Kubernetes cluster
- Sets up the local container registry
- Configures persistent volumes
- Applies initial Kubernetes configurations

### Step 3: Verify Core Components

Wait for the initial deployments to complete:

```shell
ansible-playbook $PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags=bootstrap
```

!!! info
    This command verifies that RisingWave, LocalStack, and Kafka are properly deployed and ready.

#### RisingWave Status

Verify RisingWave deployment:

```shell
kubectl get pods,svc -n risingwave
```

You should see all pods in the `Running` state with services properly configured.

#### LocalStack Status

Check LocalStack deployment:

```shell
kubectl get pods,svc -n localstack
```

You should see the LocalStack pod running and service available.

#### Kafka Status

Verify the Kafka cluster:

```shell
kubectl get pods,kafka,svc -n kafka
```

The Kafka cluster should show as ready with KRaft metadata state.

## Deploying Apache Polaris

### About Polaris Images

!!! warning "Image Availability"
    Apache Polaris does not currently publish official container images. This project uses prebuilt images or allows building from source.

You can use prebuilt images:

```shell
docker pull ghcr.io/snowflake-labs/polaris-local-forge/apache-polaris-server-pgsql
docker pull ghcr.io/snowflake-labs/polaris-local-forge/apache-polaris-admin-tool-pgsql
```

Or build images locally:

```shell
task images
```

When building locally, update the following files with your image references:
- `k8s/polaris/deployment.yaml`
- `k8s/polaris/bootstrap.yaml`
- `k8s/polaris/purge.yaml`

### Deploy Polaris

Apply the Kubernetes manifests:

```shell
kubectl apply -k $PROJECT_HOME/k8s/polaris
```

Verify the Polaris deployment:

```shell
ansible-playbook $PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags polaris
```

You should see the Polaris pod running, the bootstrap job completed, and PostgreSQL running.

## Accessing Services

Once everything is deployed, you can access the services using the following endpoints:

| Service        | URL/Endpoint                | Credentials/Notes |
|----------------|-----------------------------|--------------------|
| Polaris UI     | http://localhost:18181      | See `.bootstrap-credentials.env` file |
| LocalStack     | http://localhost:14566      | `test/test` for AWS credentials |
| Kafka          | localhost:19094             | Set `RPK_BROKERS=localhost:19094` |
| RisingWave SQL | localhost:14567             | User: `root`, No password, Database: `dev` |

!!! success "Next Steps"
    With your local cloud environment ready, you can now proceed to the next chapter to set up the Iceberg catalog and start working with the balloon game analytics pipeline.
