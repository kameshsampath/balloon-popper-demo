# Running the Application

## Learning Objectives

By the end of this chapter, you will:

- Generate simulated balloon game events and send them to Apache Kafka
- Visualize real-time analytics using the Streamlit dashboard
- Understand the data flow from event generation to visualization

## Generating Game Events

The repository includes a [streaming data generator](https://github.com/kameshsampath/balloon-popper-demo/tree/main/packages/generator) that simulates balloon pop events and sends them to Kafka. These events will then be processed by RisingWave and stored in Iceberg tables.

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
    The generator will continuously produce random balloon pop events from various players with different balloon colors and scores. These events are sent to the Kafka topic configured in your environment defaults to topic `balloon-game`.

## Visualizing the Data

The project includes a Streamlit dashboard that visualizes the real-time analytics derived from the game events.

### Starting the Dashboard

1. Open a new terminal
2. Run the following command:

```shell
task streamlit
```

3. Your browser should automatically open to the dashboard URL typically <http://localhost:8501>.

### Dashboard Features

The dashboard provides several visualizations:

- **Leaderboard**: Shows top players ranked by total score
- **Color Performance**: Displays which balloon colors yield the highest points
- **Player Progress**: Tracks individual player performance over time
- **Bonus Hits**: Visualizes the distribution of bonus hits across players and colors

!!! tip
    You can filter and interact with the visualizations to explore different aspects of the game data.

We will explore more about these visualizations in [Analytics Dashboards](./dashboards.md) chapter.

## Next Steps

Now that you have your application running with simulated data, you can:

- Modify the generator to create different patterns of game events
- Explore the RisingWave materialized views that power the analytics
- Customize the Streamlit dashboard to add new visualizations
- Analyze the Iceberg table structures and query optimization

In the next chapter, we'll go through the verification process to ensure data is flowing correctly through each component of the pipeline.