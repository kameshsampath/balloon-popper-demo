# Setup Iceberg Catalog using Apache Polaris

The Polaris server does not yet have any catalogs. Run the following script to set up your first catalog, principal, principal role, catalog role, and grants.

By the end of this chapter you would have:

- Created s3 bucket
- Created Catalog named `balloon-game`
- Created Principal `super_user` with Principal Role `admin`
- Created Catalog Role `sudo`, assign the role to Principal Role `admin`
- Granted the Catalog Role `sudo` to manage catalog via `CATALOG_MANAGE_CONTENT` role. This will make the principals with role `admin` able to manage the catalog.
- Created Iceberg database named `balloon_pops`

!!!NOTE
    All values can be adjusted via the [defaults](../../polaris-forge-setup/defaults/main.yml)

## Environment variables

```shell
# just avoid colliding with existing AWS profiles
unset AWS_PROFILE
export AWS_ENDPOINT_URL=http://localstack.localstack:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
```

Run the following command to create the Catalog:

```shell
$PROJECT_HOME/polaris-forge-setup/catalog_setup.yml
```

## Setup Sources and Sink

As part of this demo we will drain all the messages from Kafka to Iceberg tables. In streaming word we call it as draining sources to sink.

The Iceberg database `balloon_pops` will hold all sink tables that will be created in the upcoming sections.

### Generate Source and Sink SQL Scripts

!!!NOTE
    Since Source and Sink might have sensitive values we will generate them.
    Both [source.sql](./scripts/source.sql) and [sink.sql](./scripts/sink.sql) are ignored by git.

Run the following command to generate sources and sink scripts,

```shell
$PROJECT_HOME/polaris-forge-setup/generate_source_sinks.yml
```

### Source

Set up sources in Risingwave to consume messages from Kafka and sink into Iceberg tables:

```shell
psql -f $PROJECT_HOME/scripts/source.sql
```

### Sink

Setup sinks to drain the messages to Iceberg Tables

```shell
psql -f $PROJECT_HOME/scripts/sink.sql
```