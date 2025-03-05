# Troubleshooting

This guide provides solutions for common issues you might encounter when running the Balloon Popper Game analytics platform.

## No Data in Sinks

If data isn't appearing in your Iceberg tables:

1. Check that Kafka is receiving events:
   ```
   rpk -X brokers=localhost:19094 topic consume balloon-game
   ```

2. Verify that the materialized views are receiving data:
   ```sql
   psql -c "SELECT COUNT(*) FROM mv_leaderboard;"
   ```

3. Check for errors in the RisingWave logs:
   ```
   kubectl logs -n default deploy/risingwave-meta
   ```
  
## Checking Component Logs

Kubernetes logs are your primary diagnostic tool. Here's how to access logs for each component:

### Polaris Server

```bash
# Check Polaris server logs
kubectl logs -f -n polaris deployment/polaris
```

!!! tip
    The `-f` flag lets you follow the logs in real-time, which is helpful when diagnosing issues as they occur.

### Polaris Bootstrap and Purge Jobs

```bash
# Check bootstrap job logs
kubectl logs -f -n polaris jobs/polaris-bootstrap

# Check purge job logs
kubectl logs -f -n polaris jobs/polaris-purge
```

A successful bootstrap will contain the following output:

```
...
Realm 'POLARIS' successfully bootstrapped.
Bootstrap completed successfully.
...
```

### Database

```bash
# Check PostgreSQL logs
kubectl logs -f -n polaris statefulset/postgresql
```

### LocalStack

```bash
# Check LocalStack logs
kubectl logs -f -n localstack deployment/localstack
```

### RisingWave

```bash
# Check RisingWave frontend logs
kubectl logs -n risingwave deployment/risingwave-frontend

# Check RisingWave compactor logs
kubectl logs -n risingwave deployment/risingwave-compactor

# Check RisingWave compute logs
kubectl logs -n risingwave statefulset/risingwave-compute

# Check RisingWave meta logs
kubectl logs -n risingwave statefulset/risingwave-meta
```

## Resetting Polaris

If you need to reset Polaris and reinstall it, follow these steps:

1. **Run the purge job**:
   ```shell
   kubectl patch job polaris-purge -p '{"spec":{"suspend":false}}'
   ```

2. **Wait for purge to complete**:
   ```shell
   kubectl logs -f -n polaris jobs/polaris-purge
   ```

3. **Remove the bootstrap job**:
   ```shell
   kubectl delete -k k8s/polaris/job
   ```

4. **Reapply the bootstrap job**:
   ```shell
   kubectl apply -k k8s/polaris/job
   ```

5. **Verify bootstrap completion**:
   ```shell
   kubectl logs -f -n polaris jobs/polaris-bootstrap
   ```

!!! warning
    Purging will delete all catalogs and data. Only perform this action when necessary.

## Common Issues and Solutions

### Polaris Server Startup Failures

If the Polaris server fails to start:

```bash
# Check events in the namespace
kubectl get events -n polaris --sort-by='.lastTimestamp'

# Check Polaris pod status
kubectl describe pod -n polaris -l app=polaris
```

!!! info "Common causes"
    - Missing configuration files
    - Incorrect environment variables
    - Database connection issues
    - Permission problems with mounted volumes

### LocalStack Connectivity Issues

If LocalStack isn't accessible:

```bash
# Check LocalStack service
kubectl get svc -n localstack

# Verify LocalStack endpoints
kubectl exec -it -n localstack deployment/localstack -- \
  aws --endpoint-url=http://localhost:4566 s3 ls
```

!!! tip "Debugging LocalStack"
    Ensure that port forwarding is working correctly if you're trying to access LocalStack from your host:
    ```bash
    kubectl port-forward -n localstack svc/localstack 14566:4566
    ```

### PostgreSQL Connection Failures

If applications can't connect to PostgreSQL:

```bash
# Check PostgreSQL service
kubectl get svc -n polaris postgresql-hl

# Verify PostgreSQL connectivity
kubectl exec -it -n polaris postgresql-0 -- pg_isready -h localhost
```

!!! info "PostgreSQL troubleshooting"
    - Check if the PostgreSQL pod is healthy and running
    - Verify the service name and port are correct in your connection strings
    - Ensure credentials are correctly set in environment variables

### RisingWave Connection Issues

If you can't connect to RisingWave:

```bash
# Check RisingWave service
kubectl get svc -n risingwave risingwave

# Verify RisingWave is ready
kubectl get pods -n risingwave
```

!!! tip "RisingWave connectivity"
    If connecting from your host machine, make sure you're forwarding the correct port:
    ```bash
    kubectl port-forward -n risingwave svc/risingwave 14567:4567
    ```

### Kafka Troubleshooting

If Kafka isn't receiving or processing messages:

```bash
# Check Kafka pods and statefulsets
kubectl get pods,kafka -n kafka

# Check bootstrap service
kubectl get svc -n kafka my-cluster-kafka-bootstrap

# List Kafka topics
kubectl exec -n kafka my-cluster-dual-role-0 -- \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

!!! info "Kafka debugging tips"
    - Verify the topic exists using the list command above
    - Check consumer group status to see if consumers are processing messages
    - Inspect broker logs for connection or authorization errors

## Collecting Additional Diagnostics

For persistent issues, collect comprehensive diagnostics:

```bash
# Get all resources in the relevant namespace
kubectl get all -n polaris

# Dump complete pod descriptions
kubectl describe pods -n polaris > polaris-pods.txt

# Collect logs from all containers
for pod in $(kubectl get pods -n polaris -o name); do
  kubectl logs -n polaris $pod > ${pod##*/}.log
done
```

!!! success "Next steps if still unresolved"
    If you've gone through all the troubleshooting steps and still have issues:
    
    1. Check the GitHub issues page for similar problems
    2. Try redeploying the entire stack with `$PROJECT_HOME/bin/cleanup.sh` followed by `$PROJECT_HOME/bin/setup.sh`
    3. Verify that your Docker resources (CPU/Memory) are sufficient