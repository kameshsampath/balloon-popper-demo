
# Setup Sources and Sink

As part of this demo we will drain all the messages from Kafka to Iceberg tables. In streaming word we call it as draining sources to sink.

The Iceberg database `balloon_pops` will hold all sink tables that will be created in the upcoming sections.

## Generate Source and Sink SQL Scripts

!!!NOTE
    Since Source and Sink might have sensitive values we will generate them.
    Both [source.sql](./scripts/source.sql) and [sink.sql](./scripts/sink.sql) are ignored by git.

Run the following command to generate sources and sink scripts,

```shell
$PROJECT_HOME/polaris-forge-setup/generate_source_sinks.yml
```

## Source

Set up sources in Risingwave to consume messages from Kafka and sink into Iceberg tables:

```shell
psql -f $PROJECT_HOME/scripts/source.sql
```

## Sink

Setup sinks to drain the messages to Iceberg Tables

```shell
psql -f $PROJECT_HOME/scripts/sink.sql
```

__TODO__: Explain the source and sinks