# Balloon Popper Game Analytics: A Streaming Data Demo

## Overview

This demonstration showcases a complete streaming analytics pipeline that processes real-time data from a balloon popping game. The project illustrates modern data architecture patterns by combining stream processing with data lake storage and interactive visualizations.

## Architecture

![Balloon Popper Game Architecture](images/architecture-diagram.png)

*Note: Architecture diagram to be added*

## Core Components

### Data Generation
- **Balloon Popper Game**: Generates events when players pop balloons of different colors
- **Kafka**: Streams game events in real-time for immediate processing

### Stream Processing
- **RisingWave**: Processes streaming data with SQL, creating materialized views for analytics
- **Apache Polaris**: Manages Iceberg table metadata via REST catalog service
- **LocalStack S3**: Emulates AWS S3 for local storage of Iceberg data files

### Data Storage
- **Apache Iceberg**: Provides table format for analytics with schema evolution and time travel
- **Data Lake**: Stores processed data for both real-time and historical analysis

### Visualization
- **Streamlit Dashboard**: Delivers interactive visualizations of game metrics
- **Real-time Insights**: Shows leaderboards, player statistics, and color performance metrics

## Key Features

### Stream Processing Capabilities
- Real-time aggregations of player scores and balloon pop statistics
- Windowed analytics for time-based performance tracking
- Continuous processing of game events with sub-second latency

### Data Management
- Schema evolution supported through Apache Iceberg
- Merge-on-read optimizations for frequently updated metrics
- Partitioning strategies optimized for different query patterns

### Interactive Analytics
- Live leaderboards showing top-performing players
- Color-specific metrics tracking most valuable balloon types
- Time-series visualizations of game performance trends

## Use Cases Demonstrated

This demo illustrates patterns applicable to various real-world streaming analytics scenarios:

- **Gaming Analytics**: Player behavior, performance tracking, and engagement metrics
- **IoT Data Processing**: Sensor data aggregation and real-time monitoring
- **Financial Services**: Transaction monitoring and fraud detection patterns
- **E-commerce**: Real-time inventory and user behavior tracking

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Event Streaming | Apache Kafka | Real-time data transport |
| Stream Processing | RisingWave | SQL-based stream processing |
| Metadata Management | Apache Polaris | Iceberg REST catalog |
| Storage | Apache Iceberg + S3 | Table format and object storage |
| Visualization | Streamlit | Interactive dashboards |
| Infrastructure | Kubernetes (K3d) | Container orchestration |
| Cloud Emulation | LocalStack | Local AWS service emulation |

## Getting Started

This tutorial will guide you through:

1. Setting up the local development environment
2. Deploying the necessary infrastructure components
3. Configuring the Apache Polaris catalog and Iceberg tables
4. Running the event generator to produce game data
5. Exploring the Streamlit dashboard for real-time analytics

Let's begin with the environment setup in the next chapter.