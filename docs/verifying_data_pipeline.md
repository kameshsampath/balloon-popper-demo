# Verifying the Data Pipeline

## Learning Objectives

By the end of this chapter, you will:

- Understand how to verify your streaming data pipeline is working correctly
- Learn to check data in Kafka using the rpk CLI
- Master querying RisingWave materialized views
- Examine data in Iceberg tables using PyIceberg with REST Catalog
- Gain insights into common troubleshooting techniques

## Prerequisites

Before proceeding with verification:

1. Complete the setup in the "Implementing the Data Pipeline" chapter
2. Generate test data as described in the "Running the Application" chapter

!!! note
    This verification should be performed after you've successfully set up the pipeline components and generated game data using the simulator.

## Verification Process

### Step 1: Check Kafka Messages

First, check that events are being published to Kafka using the `rpk` CLI tool:

```shell
rpk topic consume \
  -X brokers={{ balloon_game_kafka_bootstrap_servers }} \
  {{ balloon_game_kafka_topic }} --pretty-print
```

This should display a stream of JSON messages similar to:

```json
{
  "player": "Cosmic Phoenix",
  "balloon_color": "blue",
  "score": 150,
  "favorite_color_bonus": true,
  "event_ts": "2025-02-17T13:59:04.453717Z"
}
```

If you're seeing messages like this, your event generator is working correctly and sending data to Kafka.

### Step 2: Check RisingWave Configuration

Next, ensure that all components are properly configured in RisingWave:

```shell
psql
```

Once connected to the RisingWave shell, run these commands to verify the setup:

```sql
-- Check sources
SHOW SOURCES;

-- Check materialized views
SHOW MATERIALIZED VIEWS;

-- Check sinks
SHOW SINKS;
```

You should see output similar to:

```text
dev=> show sources;
        Name         
---------------------
 balloon_game_events
(1 row)

dev=> show materialized views;
            Name             
-----------------------------
 mv_balloon_colored_pops
 mv_leaderboard
 mv_color_performance_trends
 mv_balloon_color_stats
 mv_realtime_scores
(5 rows)

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

### Step 3: Verify Data in Materialized Views

Check that data is appearing in the materialized views:

```sql
-- Check leaderboard
SELECT * FROM mv_leaderboard LIMIT 5;

-- Check color stats
SELECT * FROM mv_balloon_color_stats LIMIT 5;

-- Check time-windowed data
SELECT * FROM mv_realtime_scores 
WHERE window_start > now() - INTERVAL '5 minutes'
LIMIT 5;
```

If you see data in these views, it confirms that:
- Kafka is correctly receiving events
- RisingWave is successfully processing the events
- The materialized views are computing aggregations as expected

### Step 4: Verify Data in Iceberg Tables

The most comprehensive way to verify the data in Iceberg tables is to use the [workbook.ipynb notebook](https://github.com/kameshsampath/balloon-popper-demo/blob/main/notebooks/workbook.ipynb). This notebook contains cells for querying and analyzing data from all tables.

Alternatively, you can use the following Python code to query your Iceberg tables using PyIceberg with REST Catalog:

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

### Step 5: Validate End-to-End Data Flow

To validate the complete data flow:

1. Check event counts in Kafka using rpk:
   ```shell
   rpk topic consume \
     -X brokers={{ balloon_game_kafka_bootstrap_servers }} \
     {{ balloon_game_kafka_topic }} -n 1 | wc -l
   ```

2. Compare counts between materialized views and Iceberg tables:
   ```sql
   -- In RisingWave
   SELECT COUNT(*) FROM mv_leaderboard;
   ```
   
   ```python
   # In Python
   table = catalog.load_table(f"{namespace}.leaderboard")
   print(f"Iceberg record count: {len(list(table.scan()))}")
   ```

3. Verify data freshness:
   ```sql
   -- In RisingWave
   SELECT MAX(event_ts) FROM mv_leaderboard;
   ```
   
   ```python
   # In Python
   from datetime import datetime, timezone
   records = list(table.scan())
   if records:
       latest_ts = max(r[3] for r in records)  # Assuming event_ts is at index 3
       now = datetime.now(timezone.utc)
       print(f"Latest event: {latest_ts}")
       print(f"Age: {now - latest_ts}")
   ```

## Troubleshooting

If you encounter issues during verification, here are some common problems and solutions:

### No Data in Views or Tables

If no data appears:

1. Check Kafka topic existence and message count:
   ```shell
   rpk topic list
   rpk topic consume -X brokers={{ balloon_game_kafka_bootstrap_servers }} {{ balloon_game_kafka_topic }} -n 1
   ```

2. Verify that the events are being generated correctly:
   ```shell
   # Look at generator logs
   tail -f $PROJECT_HOME/packages/balloon-pop-events/app.log
   ```

3. Check for errors in RisingWave logs:
   ```shell
   kubectl logs -n default deploy/risingwave-meta
   ```
   And 
   ```shell
   kubectl logs -n default deploy/risingwave-compute
   ```

### Data in Views but Not in Tables

If data appears in materialized views but not in Iceberg tables:

1. Check sink status:
   ```sql
   SHOW SINK STATUS;
   ```

2. Verify Polaris connectivity:
   ```shell
   curl {{ plf_polaris_catalog_uri }}/api/v1/config
   ```

3. Check S3 access:
   ```shell
   aws --endpoint-url={{ plf_aws_endpoint_url }} s3 ls
   ```

### Inconsistent Data

If you see inconsistent data across the pipeline:

1. Check for schema mismatches between sources, views, and sinks
2. Verify that time zones are handled consistently
3. Look for data type conversion issues

## Key Takeaways

When verifying your streaming data pipeline, remember these principles:

1. **Verify at each stage**: Check data at every step in the pipeline
2. **Compare counts**: Make sure record counts match between sources and destinations
3. **Check data freshness**: Ensure that recent events are being processed
4. **Validate data quality**: Look for unexpected null values or incorrect formats

These verification steps are essential not just for this demo, but for any production streaming data pipeline to ensure data quality and reliability.

In the next chapter, we'll explore how to build interactive dashboards to visualize this data.