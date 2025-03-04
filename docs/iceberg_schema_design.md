# Iceberg Schema Design for Real-Time Game Analytics

## Learning Objectives

By the end of this chapter, you will:

- Understand how to design Iceberg tables for streaming game analytics data
- Learn effective partitioning strategies for different query patterns
- Gain insights into optimizing sort orders for performance
- Master the configuration of write properties for efficient updates
- See how to structure tables for various analytical perspectives (player performance, time-based analysis, and color-based trends)

## Context and Overview

Our balloon pop game generates a stream of events when players interact with the game. These events are sent to Kafka and need to be stored in a way that enables both real-time dashboards and historical analysis.

The `balloon_pops` database is designed with five Iceberg tables, each focusing on different analytical dimensions:

- **Leaderboard**: Tracks overall player performance
- **Balloon Color Stats**: Records statistics by balloon color for each player
- **Realtime Scores**: Captures time-windowed scoring data
- **Balloon Colored Pops**: Tracks detailed pop statistics in time windows
- **Color Performance Trends**: Analyzes effectiveness of different balloon colors

All tables use Iceberg Format Version 2, enabling advanced features like merge-on-read operations for efficient updates without rewriting entire files—particularly important for frequently updated gaming data.

!!! important
    Throughout this tutorial, we'll explore common design patterns and trade-offs in schema design. Pay special attention to how partitioning strategies differ based on expected query patterns.

## Table Specifications

### Leaderboard

**Table Identifier**: `balloon_pops.leaderboard`

#### Schema

| Field ID | Field Name | Data Type | Required | Description |
|----------|------------|-----------|----------|-------------|
| 1 | player | STRING | Yes | Player identifier |
| 2 | total_score | LONG | Yes | Player's cumulative score |
| 3 | bonus_hits | LONG | Yes | Number of bonus hits achieved |
| 4 | event_ts | TIMESTAMPTZ | Yes | Timestamp when the event occurred |

#### Partitioning

The table is partitioned by:

- Day (from `event_ts`)
- `player`

This partitioning strategy optimizes queries filtering by date or specific players.

#### Sort Order

Data is sorted by:

1. `total_score` (DESC)
2. `bonus_hits` (DESC)

This sorting enables efficient retrieval of top-scoring players.


#### Optimized For

- Querying leaderboard data by day
- Filtering operations by player
- Fast retrieval of top-scoring players
- Efficient upsert operations with merge-on-read configuration

---

### Balloon Color Stats

**Table Identifier**: `balloon_pops.balloon_color_stats`

#### Schema

| Field ID | Field Name | Data Type | Required | Description |
|----------|------------|-----------|----------|-------------|
| 1 | player | STRING | Yes | Player identifier |
| 2 | balloon_color | STRING | Yes | Color of the balloon |
| 3 | points_by_color | LONG | Yes | Points earned for specific balloon color |
| 4 | bonus_hits | LONG | Yes | Number of bonus hits achieved |
| 5 | event_ts | TIMESTAMPTZ | Yes | Timestamp when the event occurred |

#### Partitioning

The table uses a multi-level partitioning strategy:

- Day (from `event_ts`)
- `balloon_color`
- `player`

This allows efficient queries when filtering by any combination of these dimensions.

#### Sort Order

Data is sorted by:

1. `points_by_color` (DESC)
2. `bonus_hits` (DESC)

This sorting prioritizes high-scoring color statistics.

#### Optimized For

- Querying balloon color statistics by day
- Filtering by balloon color and/or player
- Fast retrieval of top-scoring color statistics
- Analysis of performance by color across players
- Efficient upsert operations

---

## Time Series

### Realtime Scores

**Table Identifier**: `balloon_pops.realtime_scores`

#### Schema

| Field ID | Field Name | Data Type | Required | Description |
|----------|------------|-----------|----------|-------------|
| 1 | player | STRING | Yes | Player identifier |
| 2 | total_score | LONG | Yes | Player's cumulative score |
| 3 | window_start | TIMESTAMPTZ | Yes | Start timestamp of the scoring window |
| 4 | window_end | TIMESTAMPTZ | Yes | End timestamp of the scoring window |

#### Partitioning

The table is partitioned by:

- Hour (from `window_start`)

This enables efficient time-based queries and analysis.

#### Write Properties

| Property | Value | Description |
|----------|-------|-------------|
| format-version | 2 | Enables advanced Iceberg features |

#### Optimized For

- Time-series analysis of player scores within defined windows
- Hourly aggregation and querying
- Real-time tracking of player performance
- Temporal filtering based on scoring window start time

---

### Balloon Colored Pops

**Table Identifier**: `balloon_pops.balloon_colored_pops`

#### Schema

| Field ID | Field Name | Data Type | Required | Description |
|----------|------------|-----------|----------|-------------|
| 1 | player | STRING | Yes | Player identifier |
| 2 | balloon_color | STRING | Yes | Color of the balloon |
| 3 | balloon_pops | LONG | Yes | Number of balloons popped |
| 4 | points_by_color | LONG | Yes | Points earned for specific balloon color |
| 5 | bonus_hits | LONG | Yes | Number of bonus hits achieved |
| 6 | window_start | TIMESTAMPTZ | Yes | Start timestamp of the scoring window |
| 7 | window_end | TIMESTAMPTZ | Yes | End timestamp of the scoring window |

#### Partitioning

The table is partitioned by:

- Hour (from `window_start`)
- `player`

This dual partitioning strategy optimizes for both time-based and player-specific queries.

#### Sort Order

Data is sorted by:

- `balloon_color` (ASC)

This sorting enhances performance for color-based filtering.

#### Write Properties

| Property | Value | Description |
|----------|-------|-------------|
| format-version | 2 | Enables advanced Iceberg features |

#### Optimized For

- Tracking balloon pop statistics by color for each player
- Time-series analysis within defined windows
- Querying performance by specific time periods
- Filtering by player identifier
- Fast retrieval when filtering by balloon color

---

### Color Performance Trends

**Table Identifier**: `balloon_pops.color_performance_trends`

#### Schema

| Field ID | Field Name | Data Type | Required | Description |
|----------|------------|-----------|----------|-------------|
| 1 | balloon_color | STRING | Yes | Color of the balloon |
| 2 | avg_score_per_pop | DECIMAL(10,28) | Yes | Average score earned per balloon pop |
| 3 | total_pops | LONG | Yes | Total number of balloon pops |
| 4 | window_start | TIMESTAMPTZ | Yes | Start timestamp of the analysis window |
| 5 | window_end | TIMESTAMPTZ | Yes | End timestamp of the analysis window |

#### Partitioning

The table is partitioned by:

- Hour (from `window_start`)
- `balloon_color`

This enables efficient queries for analyzing color performance over time.

#### Sort Order

Data is sorted by:

- `balloon_color` (ASC)

This optimizes lookups for specific colors.

#### Write Properties

| Property | Value | Description |
|----------|-------|-------------|
| format-version | 2 | Enables advanced Iceberg features |

#### Optimized For

- Analyzing performance trends by balloon color over time
- Time-series analysis with hourly granularity
- Comparing efficiency metrics across different balloon colors
- Tracking popularity and effectiveness of different colors

## Key Takeaways

When designing Iceberg tables for streaming analytics, remember these principles:

1. **Match partitioning to query patterns**: Partition by time for time-series analysis, by entity (player/color) for entity-specific queries
2. **Set appropriate sort orders**: Sort by metrics you'll often use for filtering or ranking
3. **Enable merge-on-read** for frequently updated tables to improve write performance
4. **Consider multiple analytical dimensions**: Design separate tables optimized for different query patterns

These principles apply not just to game analytics, but to any streaming analytics application where you need to balance write throughput with query performance.

In the next chapter, we'll explore how to implement this data model using sources and sinks in our streaming pipeline.