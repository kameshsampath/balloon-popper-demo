# Local Cloud

In this chapter, we will guide you through the following steps:

- Prepare resources for Kubernetes Deployment
- Create local Kubernetes Cluster
- Deploy Components like Localstack, Kafka, Polaris etc.,

## Configuration

All the configuration are set via [defaults/main.yml](../polaris-forge-setup/defaults/main.yml)


| Name | Description | Default Value |
|------|------------|---------------|
| `plf_aws_endpoint_url` | LocalStack endpoint in k3s | `http://localstack.localstack:4566` |
| `plf_aws_region` | AWS region for LocalStack | `us-east-1` |
| `plf_aws_role_arn` | Default role ARN for LocalStack | `arn:aws:iam::000000000000:role/Admin` |
| `plf_api_host` | Polaris API host | `localhost` |
| `plf_api_port` | Default Polaris API port | `18181` |
| `plf_realm` | Polaris realm name | `POLARIS` |
| `plf_api_base_url` | Polaris API URL | `http://{{ plf_api_host }}:{{ plf_api_port }}` |
| `plf_polaris_log_level` | Polaris API Server Log Level | `INFO` |
| `plf_catalog_name` | Name of the Polaris catalog | `balloon-game` |
| `plf_base_s3_location` | S3 location for catalog storage | `s3://{{ plf_catalog_name }}` |
| `plf_admin_username` | Superuser for Polaris | `super_user` |
| `plf_admin_role` | Admin role name | `admin` |
| `plf_catalog_role` | Catalog role name | `sudo` |
| `plf_work_dir` | Work directory for storing credentials | `{{ playbook_dir }}/../work` |
| `plf_k8s_dir` | Kubernetes manifests directory | `{{ playbook_dir }}/../k8s` |
| `plf_polaris_dir` | Directory where polaris manifests are stored | `{{ plf_k8s_dir }}/polaris` |
| `plf_features_dir` | Directory where cluster feature manifests are stored | `{{ plf_k8s_dir }}/features` |
| `plf_sql_scripts_dir` | SQL Scripts Directory | `{{ playbook_dir }}/scripts` |
| `plf_credentials_file` | Bootstrap credentials location | `{{ plf_k8s_dir }}/polaris/.bootstrap-credentials.env` |
| `plf_notebook_dir` |  | `{{ playbook_dir }}/../notebooks` |
| `plf_template_dir` |  | `{{ playbook_dir }}/templates/notebooks` |
| `plf_jpa_persistence_unit_name` |  | `polaris-dev` |
| `plf_jdbc_username` |  | `postgres` |
| `plf_polaris_database` |  | `polaris` |
| `plf_jdbc_url` |  | `jdbc:postgresql://postgresql:5432/{{ plf_polaris_database }}` |
| `balloon_game_db` |  | `balloon_pops` |
| `balloon_game_kafka_bootstrap_servers` |  | `my-cluster-kafka-bootstrap.kafka:9092` |
| `balloon_game_kafka_topic` |  | `balloon-game` |
| `polaris_catalog_uri` |  | `{{ plf_api_base_url }}/api/catalog/` |

## Prepare for Deployment

The following script will generate the required sensitive files from templates using Ansible:

```shell
ansible-playbook $PROJECT_HOME/polaris-forge-setup/prepare.yml
```

## Create the Cluster

Run the cluster setup script:

```bash
$PROJECT_HOME/bin/setup.sh
```

## Verify Components

Once the cluster is started, wait for the deployments to be ready:

```shell
ansible-playbook  $PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags=bootstrap
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

```text
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

## Deploy Apache Polaris

### Container Images

Currently, Apache Polaris does not publish any official images. The Apache Polaris images used by the repo are available at:

```
docker pull ghcr.io/snowflake-labs/polaris-local-forge/apache-polaris-server-pgsql
docker pull ghcr.io/snowflake-labs/polaris-local-forge/apache-polaris-admin-tool-pgsql
```

The images are built with PostgreSQL as database dependency.

(OR)

The project also has scripts to build them from sources locally.

Run the following command to build Apache Polaris images and push them into the local registry `k3d-registry.localhost:5000`. Update the `IMAGE_REGISTRY` env in [Taskfile](../../Taskfile.yml) and then run:

```shell
task images
```

When you build locally, please make sure to update the `k8s/polaris/deployment.yaml`, `k8s/polaris/bootstrap.yaml`, and `k8s/polaris/purge.yaml` with correct images.

### Apply Manifests

```shell
kubectl apply -k $PROJECT_HOME/k8s/polaris
```

Ensure all deployments and jobs have succeeded:

```shell
ansible-playbook  $PROJECT_HOME/polaris-forge-setup/cluster_checks.yml --tags polaris
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

## Available Services

| Service        | URL                                                  | Default Credentials                                                                                |
| -------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Polaris UI     | http://localhost:18181                               | $PROJECT_HOME/k8s/polaris/.bootstrap-credentials.env                                               |
| LocalStack     | http://localhost:14566                               | Use `test/test` for AWS credentials with Endpoint URL as http://localhost:14566                    |
| Kafka          | localhost:19094                                      | No credentials, set `RPK_BROKERS` to `localhost:19094` to start accessing the cluster              |
| Risingwave SQL | Host: localhost Port: 14567 User: root Database: dev | Use `psql` client to connect, no password set.                                                     |