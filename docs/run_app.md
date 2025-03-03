# Running the Application

## Learning Objectives

By the end of this chapter, you will:

- Generate simulated balloon game events and send them to Apache Kafka
- Visualize real-time analytics using the Streamlit dashboard
- Understand the data flow from event generation to visualization

## Generating Game Events

The repository includes a [streaming data generator](../packages/generator) that simulates balloon pop events and sends them to Kafka. These events will then be processed by RisingWave and stored in Iceberg tables.

### Event Structure

When a player pops a balloon, an event with the following structure is generated:

```json
{
  "player": "Cosmic Phoenix",
  "balloon_color": "pink",
  "score": 55,
  "favorite_color_bonus": false,
  "event_ts": "2025-02-17T13:59:00.430087Z"
}
```

If the player pops a balloon of their favorite color, they receive a bonus:

```json
{
  "player": "Cosmic Phoenix",
  "balloon_color": "blue",
  "score": 150,
  "favorite_color_bonus": true,
  "event_ts": "2025-02-17T13:59:04.453717Z"
}
```

### Starting the Generator

To start generating events:

1. Open a new terminal
2. Run the following command:

```shell
task generator-local
```

!!! info
    The generator will continuously produce random balloon pop events from various players with different balloon colors and scores. These events are sent to the Kafka topic configured in your environment.

## Visualizing the Data

The project includes a Streamlit dashboard that visualizes the real-time analytics derived from the game events.

### Starting the Dashboard

1. Open a new terminal
2. Run the following command:

```shell
task streamlit
```

3. Your browser should automatically open to the dashboard URL (typically http://localhost:8501)

### Dashboard Features

The dashboard provides several visualizations:

- **Leaderboard**: Shows top players ranked by total score
- **Color Performance**: Displays which balloon colors yield the highest points
- **Player Progress**: Tracks individual player performance over time
- **Bonus Hits**: Visualizes the distribution of bonus hits across players and colors

!!! tip
    You can filter and interact with the visualizations to explore different aspects of the game data.

## Advanced Data Exploration

For more advanced data exploration and direct interaction with the Iceberg tables:

1. Open the Jupyter notebook [workbook.ipynb](../notebooks/workbook.ipynb)
2. Use [PyIceberg](https://py.iceberg.apache.org/) to query and analyze the data

```python
# Example PyIceberg query from the workbook
from pyiceberg.catalog import load_catalog

# Load the catalog
catalog = load_catalog("balloon-game")

# List all tables
tables = catalog.list_tables(catalog_name="balloon_pops")
print(tables)

# Query a table
table = catalog.load_table("balloon_pops.leaderboard")
results = table.scan().to_arrow()
```

!!! note
    The notebook provides a more flexible environment for data scientists and analysts who want to perform custom queries and analyses beyond what's available in the dashboard.

## Verifying Data Flow

To verify that data is flowing correctly through the system:

1. Check Kafka to ensure messages are being produced:
   ```shell
   kubectl exec -n kafka my-cluster-dual-role-0 -- \
     /opt/kafka/bin/kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic balloon-game \
     --from-beginning \
     --max-messages 5
   ```

2. Check RisingWave to ensure data is being processed:
   ```shell
   psql -h localhost -p 14567 -U root -d dev -c "SELECT count(*) FROM balloon_game_source"
   ```

3. Verify data is landing in Iceberg tables via LocalStack:
   ```shell
   aws --endpoint-url=http://localhost:14566 \
     s3 ls s3://balloon-game/balloon_pops/leaderboard/ --recursive
   ```

## Next Steps

Now that you have your application running with simulated data, you can:

- Modify the generator to create different patterns of game events
- Explore the RisingWave materialized views that power the analytics
- Customize the Streamlit dashboard to add new visualizations
- Analyze the Iceberg table structures and query optimization