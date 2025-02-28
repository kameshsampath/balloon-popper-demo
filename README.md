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

Going forward we will refer to the cloned sources folder as `$PROJECT_HOME`.

## Python Environment Setup

Install the `uv` tool:

```bash
# Using pip
pip install uv

# Or using curl (Unix-like systems)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Set up Python environment:

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

> **Tip**
> Use tools like [direnv](https://direnv.net) to make it easy setting environment variables

## DNSmasq (Optional)

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

To ensure reuse and for security, files with passwords are not added to git. Currently, the following files are ignored or not available out of the box (they will be generated in upcoming steps):

- k8s/features/postgresql.yaml
- k8s/features/risingwave.yaml
- k8s/polaris/persistence.xml
- k8s/polaris/.bootstrap-credentials
- k8s/polaris/.polaris.env
- All RSA KeyPairs
- scripts/*.sql

### Prepare for Deployment

The following script will generate the required sensitive files from templates using Ansible:

```shell
$PROJECT_HOME/polaris-forge-setup/prepare.yml
```

## Create the Cluster

Run the cluster setup script:

```bash
$PROJECT_HOME/bin/setup.sh
```

Once the cluster is started, wait for the deployments to be ready:

```shell
$PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags localstack,risingwave,kafka
```

The cluster will deploy `risingwave`, `localstack` and `kafka`. You can verify them as shown in upcoming sections.

### Risingwave

To verify the deployments:

```bash
kubectl get pods,svc -n risingwave
```

Expected output:

```text
NAME                                        READY   STATUS    RESTARTS   AGE
pod/risingwave-compactor-5d5d975fb4-b74xh   1/1     Running   0          100m
pod/risingwave-compute-0                    1/1     Running   0          100m
pod/risingwave-frontend-cfff8c67c-gclcc     1/1     Running   0          100m
pod/risingwave-meta-0                       1/1     Running   0          100m
pod/risingwave-minio-866bf464fb-zh7xg       1/1     Running   0          100m
pod/risingwave-postgresql-0                 1/1     Running   0          100m

NAME                                  TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)                      AGE
service/risingwave                    NodePort    10.43.80.19    <none>        4567:31910/TCP               100m
service/risingwave-compute-headless   ClusterIP   None           <none>        5688/TCP,1222/TCP            100m
service/risingwave-meta-headless      ClusterIP   None           <none>        5690/TCP,5691/TCP,1250/TCP   100m
service/risingwave-minio              ClusterIP   10.43.5.173    <none>        9000/TCP,9001/TCP            100m
service/risingwave-postgresql         ClusterIP   10.43.97.156   <none>        5432/TCP                     100m
service/risingwave-postgresql-hl      ClusterIP   None           <none>        5432/TCP                     100m
```

### Localstack

```bash
kubectl get pods,svc -n localstack
```

Expected output:

```text
NAME                              READY   STATUS    RESTARTS   AGE
pod/localstack-86b7f56d7f-hs6vq   1/1     Running   0          76m

NAME                 TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
service/localstack   NodePort   10.43.112.185   <none>        4566:31566/TCP,...  76m
```

### Kafka

```bash
kubectl get pods,kafka,svc -n kafka
```

Expected output:

```bash
NAME                                              READY   STATUS    RESTARTS      AGE
pod/my-cluster-dual-role-0                        1/1     Running   0             101m
pod/my-cluster-entity-operator-57c4b47c85-kvlmj   2/2     Running   0             100m
pod/strimzi-cluster-operator-76b947897f-hx7bs     1/1     Running   1 (67m ago)   102m

NAME                                DESIRED KAFKA REPLICAS   DESIRED ZK REPLICAS   READY   METADATA STATE   WARNINGS
kafka.kafka.strimzi.io/my-cluster                                                  True    KRaft

NAME                                          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                        AGE
service/my-cluster-dual-role-extplain-0       NodePort    10.43.63.36     <none>        9094:31764/TCP                                 101m
service/my-cluster-kafka-bootstrap            ClusterIP   10.43.11.246    <none>        9091/TCP,9092/TCP,9093/TCP                     101m
service/my-cluster-kafka-brokers              ClusterIP   None            <none>        9090/TCP,9091/TCP,8443/TCP,9092/TCP,9093/TCP   101m
service/my-cluster-kafka-extplain-bootstrap   NodePort    10.43.197.175   <none>        9094:31905/TCP                                 101m
```

Expected output:

### Deploy Apache Polaris

#### Container Images

Currently, Apache Polaris does not publish any official images. The Apache Polaris images used by the repo are available at:

```
docker pull ghcr.io/snowflake-labs/polaris-local-forge/apache-polaris-server-pgsql
docker pull ghcr.io/snowflake-labs/polaris-local-forge/apache-polaris-admin-tool-pgsql
```

The images are built with PostgreSQL as database dependency.

(OR)

The project also has scripts to build them from sources locally.

Run the following command to build Apache Polaris images and push them into the local registry `k3d-registry.localhost:5000`. Update the `IMAGE_REGISTRY` env in [Taskfile](./Taskfile.yml) and then run:

```shell
task images
```

When you build locally, please make sure to update the `k8s/polaris/deployment.yaml`, `k8s/polaris/bootstrap.yaml`, and `k8s/polaris/purge.yaml` with correct images.

#### Apply Manifests

```shell
kubectl apply -k $PROJECT_HOME/k8s/polaris
```

Ensure all deployments and jobs have succeeded:

```shell
$PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags polaris
```

Checking for pods and services in the `polaris` namespace should display:

```text
NAME                           READY   STATUS      RESTARTS   AGE
pod/polaris-694ddbb476-m2trm   1/1     Running     0          13m
pod/polaris-bootstrap-tpkh4    0/1     Completed   0          13m
pod/postgresql-0               1/1     Running     0          100m

NAME                    TYPE           CLUSTER-IP     EXTERNAL-IP             PORT(S)          AGE
service/polaris         LoadBalancer   10.43.202.93   172.19.0.3,172.19.0.4   8181:32181/TCP   13m
service/postgresql      ClusterIP      10.43.182.31   <none>                  5432/TCP         100m
service/postgresql-hl   ClusterIP      None           <none>                  5432/TCP         100m
```

### Available Services

| Service        | URL                                                  | Default Credentials                                                                                |
|----------------|------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Polaris UI     | http://localhost:18181                               | $PROJECT_HOME/k8s/polaris/.bootstrap-credentials.env                                               |
| Adminer        | http://localhost:18080                               | PostgreSQL host will be: `postgresql.polaris`, check $FEATURES_DIR/postgresql.yaml for credentials |
| LocalStack     | http://localhost:14566                               | Use `test/test` for AWS credentials with Endpoint URL as http://localhost:14566                    |
| Kafka          | localhost:19094                                      | No credentials, set `RPK_BROKERS` to `localhost:19094` to start accessing the cluster              |
| Risingwave SQL | Host: localhost Port: 14567 User: root Database: dev | Use `psql` client to connect, no password set.                                                     |

### Setup Iceberg Catalog using Apache Polaris

With all services deployed successfully, update the environment to be like:

```shell
# just avoid colliding with existing AWS profiles
unset AWS_PROFILE
export AWS_ENDPOINT_URL=http://localstack.localstack:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
```

The Polaris server does not yet have any catalogs. Run the following script to set up your first catalog, principal, principal role, catalog role, and grants.

Next, we will do the following:

- Create s3 bucket
- Create Catalog named `balloon-game`
- Create Principal `super_user` with Principal Role `admin`
- Create Catalog Role `sudo`, assign the role to Principal Role `admin`
- Grant the Catalog Role `sudo` to manage catalog via `CATALOG_MANAGE_CONTENT` role. This will make the principals with role `admin` able to manage the catalog.
- Create Iceberg database named `balloon_pops`
- Create the principal secret in `trino` namespace

> ![NOTE]:
> All values can be adjusted via the [defaults](./polaris-forge-setup/defaults/main.yml)

```shell
$PROJECT_HOME/polaris-forge-setup/catalog_setup.yml
```

## Setup Sources and Sink

The Iceberg database `balloon_pops` will hold all sink tables that will be created in the upcoming sections.

### Generate Source and Sink SQL Scripts

> ![NOTE]
> Since Source and Sink might have sensitive values we will generate them.
> Both [source.sql](./scripts/source.sql) and [sink.sql](./scripts/sink.sql) are ignored by git.

```shell
$PROJECT_HOME/polaris-forge-setup/generate_source_sinks.yml
```
### Source

Set up sources to consume messages from Kafka and sink into Iceberg Tables:

```shell
psql -f $PROJECT_HOME/scripts/source.sql
```

### Trino

We will use `trino` as the SQL engine to query the Iceberg Tables

```shell
kubectl apply -f k8s/features/trino.yml
```

Connect to `trino` 

```shell
trino --server http://localhost:18080
```
### Sink

Setup sinks to drain the messages to Iceberg Tables

```shell
psql -f $PROJECT_HOME/scripts/sink.sql
```

## Run Application

### Simulate Data Generation

The demo repo has [streaming data generator](./packages/generator) that can be used to generate data into Kafka to be drained to Iceberg Tables.

Sample payloads that will when a balloon is popped,

```json
{
  "player": "Cosmic Phoenix",
  "balloon_color": "pink",
  "score": 55,
  "favorite_color_bonus": false,
  "event_ts": "2025-02-17T13: 59: 00.430087Z"
}
```

```json
{
  "player": "Cosmic Phoenix",
  "balloon_color": "blue",
  "score": 150,
  "favorite_color_bonus": true,
  "event_ts": "2025-02-17T13:59:04.453717Z"
}
```

Open a new terminal and run the following command,

```shell
task generator-local
```

> ![NOTE]
> We can use notebook [workbook](./notebooks/workbook.ipynb) to work with the Iceberg catalog using the [PyIceberg](https://py.iceberg.apache.org/)

###  Visualize Data using Streamlit

Open new terminal and run the following command,

```shell
task streamlit
```

## Troubleshooting

### Checking Component Logs

You can use `kubectl logs` to inspect the logs of various components:

#### Polaris Server

```bash
# Check Polaris server logs
kubectl logs -f -n polaris deployment/polaris
```
##### Purge and Bootstrap

Whenever there is a need to clean and do bootstrap again, run the following sequence of commands:

```shell
kubectl patch job polaris-purge -p '{"spec":{"suspend":false}}'
```

Wait for purge to complete:

```shell
kubectl logs -f -n polaris jobs/polaris-purge
```

Scale down bootstrap and then scale it up:

```shell
kubectl delete -k k8s/polaris/job
```

```shell
kubectl apply -k k8s/polaris/job
```

Wait for bootstrap to complete successfully:

```shell
kubectl logs -f -n polaris jobs/polaris-bootstrap
```

A successful bootstrap will have the following text in the log:

```text
...
Realm 'POLARIS' successfully bootstrapped.
Bootstrap completed successfully.
...
```

#### Bootstrap and Purge Jobs

```bash
# Check bootstrap job logs
kubectl logs -f -n polaris jobs/polaris-bootstrap

# Check purge job logs
kubectl logs -f -n polaris jobs/polaris-purge
```

#### Database

```bash
# Check PostgreSQL logs
kubectl logs -f -n polaris statefulset/postgresql
```

#### LocalStack

```bash
# Check LocalStack logs
kubectl logs -f -n localstack deployment/localstack
```

### Common Issues

1. If Polaris server fails to start:

   ```bash
   # Check events in the namespace
   kubectl get events -n polaris --sort-by='.lastTimestamp'

   # Check Polaris pod status
   kubectl describe pod -n polaris -l app=polaris
   ```

2. If LocalStack isn't accessible:

   ```bash
   # Check LocalStack service
   kubectl get svc -n localstack

   # Verify LocalStack endpoints
   kubectl exec -it -n localstack deployment/localstack -- aws --endpoint-url=http://localhost:4566 s3 ls
   ```

3. If PostgreSQL connection fails:

   ```bash
   # Check PostgreSQL service
   kubectl get svc -n polaris postgresql-hl

   # Verify PostgreSQL connectivity
   kubectl exec -it -n polaris postgresql-0 -- pg_isready -h localhost
   ```
4. If Risingwave connection fails:

   ```bash
   # Check Risingwave service
   kubectl get svc -n risingwave risingwave

   # Verify Risingwave logs
   kubectl logs -n risingwave deployment/risingwave-frontend
   # (or)
   kubectl logs -n risingwave deployment/risingwave-risingwave-compactor 
   # (or)
   kubectl logs -n risingwave statefulset/risingwave-compute 
   # (or)
   kubectl logs -n risingwave statefulset/risingwave-meta
   ```
   
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
