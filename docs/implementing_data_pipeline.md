# Implementing the Data Pipeline

## Learning Objectives

By the end of this chapter, you will:

- Understand how to configure Kafka sources to ingest game events
- Learn to set up RisingWave materialized views for stream processing
- Master the configuration of Iceberg sinks for persistent storage
- Verify the end-to-end data flow of your streaming pipeline
- Troubleshoot common issues in the data pipeline setup

## Context and Overview

In the previous chapter, we designed our Iceberg schema for game analytics. Now, we'll implement the data pipeline that will process our game events and store them in these tables.

Our implementation follows a structured approach:

1. Configure Kafka as the **source** of streaming data
2. Create materialized views in RisingWave for **processing** the data
3. Set up Iceberg tables as **sinks** for persistent storage
4. Verify the pipeline's operation with testing and validation

!!! note
    The complete data pipeline configuration is generated using Ansible playbooks, which ensures consistency and reproducibility of the setup.

## Setting Up the Pipeline

### Step 1: Generate Configuration Scripts

First, we'll generate the necessary SQL scripts using our Ansible playbook:

```shell
ansible-playbook $PROJECT_HOME/polaris-forge-setup/generate_source_sinks.yml
```

This playbook creates SQL files with the configuration for:
- Kafka sources
- RisingWave materialized views
- Iceberg sinks

The generated scripts will be placed in the `$PROJECT_HOME/scripts/` directory.

!!! note "Template Variables"
    You'll notice that the SQL scripts contain placeholders in the format of `{{ variable_name }}`. These are Jinja2 template variables that are replaced with actual values during script generation. The values for these variables are defined in the application settings file at [polaris-forge-setup/defaults/main.yml](https://github.com/kameshsampath/balloon-popper-demo/blob/main/polaris-forge-setup/defaults/main.yml).

### Step 2: Configure Kafka Sources

Next, we'll set up the Kafka source to ingest game events:

```shell
psql -f $PROJECT_HOME/scripts/source.sql
```

The `source.sql` script is generated from a Jinja template that creates a RisingWave source connecting to our Kafka topic, along with the necessary materialized views. Here's what the source configuration looks like:

```sql
-- source events from Kafka
CREATE SOURCE IF NOT EXISTS balloon_game_events (
 player string,
 balloon_color string,
 score integer,
 page_id integer,
 favorite_color_bonus boolean,
 event_ts timestamptz
)
WITH (
 connector='kafka',
 topic='{{ balloon_game_kafka_topic }}',
 properties.bootstrap.server='{{ balloon_game_kafka_bootstrap_servers }}',
 scan.startup.mode='latest'
) FORMAT PLAIN ENCODE JSON;
```

This configuration:
- Defines the schema for our game events
- Connects to the specified Kafka topic through the template variable
- Specifies JSON as the message format
- Sets the scan mode to start from the latest available message (real-time processing)

The same template also defines our materialized views, such as the leaderboard view:

```sql
-- Leaderboard stats
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_leaderboard AS
  SELECT
    player,
    sum(score) as total_score,
    count(case when favorite_color_bonus = true then 1 end) as bonus_hits,
    max(event_ts) as event_ts
  FROM balloon_game_events
  GROUP BY player;
```

### Step 3: Create RisingWave Materialized Views

The materialized views are already defined in the same Jinja template as the source. These views transform our raw event data into the format expected by our Iceberg tables.

Here are the key materialized views defined in the template:

```sql
-- Overall Color Stats
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_balloon_color_stats AS
 SELECT
   player,
   balloon_color,
   count(*) as balloon_pops,
   sum(score) as points_by_color,
   count(CASE WHEN favorite_color_bonus = true THEN 1 END) as bonus_hits,
   max(event_ts) as event_ts
 FROM balloon_game_events
 GROUP BY
   player,
   balloon_color;

-- Timeseries 
-- Leaderboard over window of 15 seconds
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_realtime_scores AS
  SELECT
    player,
    sum(score) as total_score,
    window_start,
    window_end
  FROM TUMBLE(balloon_game_events, event_ts, INTERVAL '15 SECONDS')
  GROUP BY
    player,
    window_start,
    window_end;

-- Analyze the various balloon_color pops in 15 seconds
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_balloon_colored_pops AS
 SELECT
   player,
   balloon_color,
   count(*) as balloon_pops,
   sum(score) as points_by_color,
   count(CASE WHEN favorite_color_bonus = true THEN 1 END) as bonus_hits,
   window_start,
   window_end
 FROM TUMBLE(balloon_game_events, event_ts, INTERVAL '15 SECONDS')
 GROUP BY
   player,
   balloon_color,
   window_start,
   window_end;

-- Color based performance
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_color_performance_trends AS
 SELECT
  balloon_color,
  avg(score) as avg_score_per_pop,
  count(*) as total_pops,
  window_start,
  window_end
 FROM TUMBLE(balloon_game_events, event_ts, INTERVAL '15 SECONDS')
 GROUP BY
    balloon_color,
    window_start,
    window_end;
```

Note the use of `TUMBLE` windows to create 15-second time slices for our time-series analysis. This allows us to track how performance changes over time in a consistent way.

### Step 4: Configure Iceberg Sinks

Now that we have our materialized views set up, we can configure the sinks that will write data to our Iceberg tables:

```shell
psql -f $PROJECT_HOME/scripts/sink.sql
```

The `sink.sql` script is also generated from a Jinja template and creates sinks for each of our materialized views. Here's an example sink configuration:

```sql
CREATE SINK IF NOT EXISTS leaderboard
 FROM mv_leaderboard
 WITH (
   connector='iceberg',
   type = 'append-only',
   force_append_only='true',
   database.name = '{{ balloon_game_db }}',
   table.name = 'leaderboard',

   warehouse.path = '{{ plf_catalog_name }}',
   catalog.name = '{{ plf_catalog_name }}',
   catalog.type = 'rest',
   catalog.uri = '{{ plf_polaris_catalog_uri }}',
   catalog.credential = '{{ principal_client_id }}:{{ principal_client_secret }}',
   catalog.scope='PRINCIPAL_ROLE:ALL',
   s3.endpoint = '{{ plf_aws_endpoint_url }}',
   s3.access.key = '{{ plf_aws_access_key_id  | default("test") }}',
   s3.secret.key = '{{ plf_aws_secret_access_key  | default("test") }}',
   s3.region = '{{ plf_aws_region }}',
   s3.path.style.access = 'true'
);
```

This configuration:
- Creates a sink named `leaderboard` from the `mv_leaderboard` materialized view
- Uses the Iceberg connector to write to our Iceberg table
- Specifies `append-only` type with `force_append_only` set to true for better performance
- Uses template variables for database and catalog configuration
- Configures S3 storage with the appropriate endpoint, region, and credentials
- Sets up Apache Polaris as the REST catalog service
- Provides proper authentication and access control through credentials and scope

Similar sink configurations are created for each of our materialized views, including `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, and `color_performance_trends`.

## Verifying the Pipeline

After setting up the pipeline, it's important to verify that everything is working correctly.

### Check RisingWave Configuration

Run the following command to shell into the RisingWave interactive shell:

```shell
psql
```

#### List All Sources

```sql
SHOW SOURCES;
```

Expected output:

```text
dev=> show sources;
        Name         
---------------------
 balloon_game_events
(1 row)
```

#### List All Materialized Views

```sql
SHOW MATERIALIZED VIEWS;
```

Expected output:

```text
dev=> show materialized views;
            Name             
-----------------------------
 mv_balloon_colored_pops
 mv_leaderboard
 mv_color_performance_trends
 mv_balloon_color_stats
 mv_realtime_scores
(5 rows)
```

#### List All Sinks

```sql
SHOW SINKS;
```

Expected output:

```text
dev=> show sinks;
           Name           
--------------------------
 color_performance_trends
 realtime_scores
 balloon_colored_pops
 balloon_color_stats
 leaderboard
(5 rows)
```

### Verify Data Flow

To ensure data is flowing through the pipeline correctly:

1. **Generate test data**: This verification should be done after completing the "run_app.md" section, which explains how to generate data into Kafka using the event generator:

   ```shell
   python $PROJECT_HOME/packages/balloon-pop-events/main.py --players 5 --duration 60
   ```

2. **Check data in materialized views**:

   ```sql
   SELECT * FROM mv_leaderboard LIMIT 5;
   ```

3. **Verify data in Iceberg tables**: You can use the [workbook.ipynb notebook](https://github.com/kameshsampath/balloon-popper-demo/blob/main/notebooks/workbook.ipynb) for comprehensive verification and querying of the data.

4. **Query using PyIceberg with REST Catalog**:

   ```python
   import os
   from pathlib import Path
   
   from pyiceberg.catalog.rest import RestCatalog
   from pyiceberg.exceptions import NamespaceAlreadyExistsError
   
   POLARIS_BASE_URI="http://localhost:18181"
   # IMPORTANT!!! /api/catalog or get the prefix from your OpenCatalog instance
   CATALOG_URI = f"{POLARIS_BASE_URI}/api/catalog"
   OAUTH2_SERVER_URI= f"{POLARIS_BASE_URI}/api/catalog/v1/oauth/tokens"
   catalog_name = "balloon-game"
   # database
   namespace = "balloon_pops"
   catalog = RestCatalog(
       name=catalog_name,
       **{
           "uri": CATALOG_URI,
           "credential": f"{client_id}:{client_secret}",
           "header.content-type": "application/vnd.api+json",
           "header.X-Iceberg-Access-Delegation": "vended-credentials",
           "header.Polaris-Realm": realm,
           "oauth2-server-uri": OAUTH2_SERVER_URI,
           "warehouse": catalog_name,
           "scope": "PRINCIPAL_ROLE:ALL",
       },
   )
   
   # Load and query a table
   table = catalog.load_table(f"{namespace}.leaderboard")
   
   # Count records
   print(f"Record count: {len(list(table.scan()))}")
   
   # Display sample data
   for record in list(table.scan())[:5]:
       print(record)
   ```

## Troubleshooting

If you encounter issues with the data pipeline, here are some common problems and solutions:

### No Data in Sinks

If data isn't appearing in your Iceberg tables:

1. Check that Kafka is receiving events:
   ```
   kafkacat -b {{ balloon_game_kafka_bootstrap_servers }} -t {{ balloon_game_kafka_topic }} -C
   ```

2. Verify that the materialized views are receiving data:
   ```sql
   SELECT COUNT(*) FROM mv_leaderboard;
   ```

3. Check for errors in the RisingWave logs:
   ```
   kubectl logs -n default deploy/risingwave-frontend
   ```

### Template Variable Issues

If you encounter errors related to the Jinja template variables:

1. Make sure all required variables are defined in your environment or Ansible variables
2. Verify that the Ansible playbook has access to the necessary credentials
3. Check the generated SQL scripts to ensure variables were properly substituted

### Connectivity Issues

If the pipeline components can't connect to each other:

1. Verify that Apache Polaris is accessible:
   ```
   curl {{ plf_polaris_catalog_uri }}/api/v1/config
   ```

2. Check S3 connectivity:
   ```
   aws --endpoint-url={{ plf_aws_endpoint_url }} s3 ls
   ```

3. Ensure Kafka is running and accessible:
   ```
   kubectl get pods | grep kafka
   ```

### Schema Mismatch Errors

If you see schema mismatch errors:

1. Compare the schema in the materialized view with the Iceberg table schema
2. Ensure data types are compatible between RisingWave and Iceberg
3. You may need to drop and recreate the sink with the correct schema

## Key Takeaways

When implementing a streaming data pipeline for game analytics, remember these principles:

1. **Start simple**: Begin with a basic pipeline and add complexity incrementally
2. **Verify each step**: Test each component individually before connecting them
3. **Monitor continuously**: Set up logging and monitoring to catch issues early
4. **Use configuration management**: Generate configuration with tools like Ansible to ensure consistency

In the next chapter, we'll explore how to build interactive dashboards on top of our Iceberg tables to visualize the game analytics data.