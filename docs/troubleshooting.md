
# Troubleshooting

## Checking Component Logs

You can use `kubectl logs` to inspect the logs of various components:

### Polaris Server

```bash
# Check Polaris server logs
kubectl logs -f -n polaris deployment/polaris
```

#### Polaris Server

```bash
# Check Polaris server logs
kubectl logs -f -n polaris deployment/polaris
```

#### Purge and Bootstrap

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

### Bootstrap and Purge Jobs

```bash
# Check bootstrap job logs
kubectl logs -f -n polaris jobs/polaris-bootstrap

# Check purge job logs
kubectl logs -f -n polaris jobs/polaris-purge
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

## Common Issues

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
