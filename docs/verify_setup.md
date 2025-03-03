## Run Application

By the end of this chapter you would have 

- Simulated data generation, sending  balloon game messages to the Apache Kafka Cluster
- Visualized the data using Streamlit

## Simulate Data Generation

The demo repo has [streaming data generator](../packages/generator) that can be used to generate data into Kafka to be drained to Iceberg Tables.

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

!!!NOTE
    We can use notebook [workbook](../notebooks/workbook.ipynb) to work with the Iceberg catalog using the [PyIceberg](https://py.iceberg.apache.org/)

## Visualize Data using Streamlit

Open new terminal and run the following command,

```shell
task streamlit
```
