# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

import argparse
import asyncio
import json
import os
import random
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from common.log.logger import get_logger
from common.stream.models import GAME_CONFIG, GameEvent

load_dotenv()


logger = get_logger("balloon_game_producer")


class BalloonGameGenerator:
    def __init__(self, bonus_probability: float):
        self.bonus_probability = bonus_probability
        self.cartoon_characters = list(GAME_CONFIG.character_favorites.keys())
        self.balloon_colors = list(GAME_CONFIG.colors.keys())

    def generate_pop(self, player_name) -> GameEvent:
        player_character = random.choice(self.cartoon_characters)

        if random.random() < self.bonus_probability:
            balloon_color = random.choice(
                GAME_CONFIG.character_favorites[player_character]
            )
        else:
            balloon_color = random.choice(self.balloon_colors)

        is_favorite_hit = balloon_color in GAME_CONFIG.character_favorites.get(
            player_character, []
        )
        logger.debug(f"Player Bonus {player_character} ? {is_favorite_hit}")

        score = GAME_CONFIG.colors.get(balloon_color, 0)
        if is_favorite_hit:
            score = score * 2

        event = GameEvent(
            player=player_name,
            balloon_color=balloon_color,
            score=score,
            favorite_color_bonus=is_favorite_hit,
            event_ts=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        return event


class AsyncBalloonPopProducer:
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        max_batch_size: int,
        delay: float,
        generator_config: dict,
    ):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            max_batch_size=max_batch_size,
        )
        self.topic = topic
        self.delay = delay
        self.generator = BalloonGameGenerator(generator_config["bonus_probability"])
        logger.info(f"Generator config {generator_config}")
        self.player_pool = [
            self.generate_player_name() for _ in range(generator_config["num_players"])
        ]

    async def send_pop(self, pop_data: GameEvent):
        await self.producer.send_and_wait(self.topic, pop_data)
        logger.info(f"{pop_data}")

    def generate_player_name(self):
        adjectives = ["Swift", "Bouncy", "Cosmic", "Lucky", "Mighty", "Gentle", "Wild"]
        nouns = ["Balloon", "Cloud", "Star", "Wind", "Phoenix", "Dragon", "Spirit"]

        return f"{random.choice(adjectives)} {random.choice(nouns)}"

    async def run(self):
        await self.producer.start()
        try:
            while True:
                player = random.choice(self.player_pool)
                pop_data = self.generator.generate_pop(player)
                await self.send_pop(pop_data.model_dump())
                await asyncio.sleep(self.delay)
        finally:
            await self.producer.stop()


# Default configuration

CONFIG = {
    "kafka": {
        "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19094"),
        "topic": os.getenv("KAFKA_TOPIC", "balloon-game"),
        "max_batch_size": 16384,
        "delay": float(os.getenv("DELAY", "1.0")),
    },
    "generator": {
        "num_players": int(os.getenv("NUM_PLAYERS", "10")),
        "bonus_probability": float(os.getenv("BONUS_PROBABILITY", "0.15")),
    },
    "logging": {
        "level": os.getenv("APP_LOG_LEVEL", "INFO"),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Balloon Game Data Generator")

    # Kafka settings
    kafka_group = parser.add_argument_group("Kafka Settings")
    kafka_group.add_argument(
        "--bootstrap-servers",
        default=CONFIG["kafka"]["bootstrap_servers"],
    )
    kafka_group.add_argument("--topic", default=CONFIG["kafka"]["topic"])
    kafka_group.add_argument(
        "--max-batch-size", type=int, default=CONFIG["kafka"]["max_batch_size"]
    )
    kafka_group.add_argument("--delay", type=float, default=CONFIG["kafka"]["delay"])

    # Generator settings
    gen_group = parser.add_argument_group("Generator Settings")
    gen_group.add_argument(
        "--num-players",
        type=int,
        default=CONFIG["generator"]["num_players"],
        help="Number of players to simulate",
    )
    gen_group.add_argument(
        "--bonus-probability",
        type=float,
        default=CONFIG["generator"]["bonus_probability"],
        help="Probability of getting favorite color (0-1)",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=CONFIG["logging"]["level"],
    )

    return parser.parse_args()


async def run():
    args = parse_args()

    global logger
    logger.setLevel(args.log_level)

    generator_config = {
        "bonus_probability": args.bonus_probability,
        "num_players": args.num_players,
    }

    producer = AsyncBalloonPopProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        max_batch_size=args.max_batch_size,
        delay=args.delay,
        generator_config=generator_config,
    )

    try:
        logger.info("Starting balloon game producer...")
        await producer.run()
    except KeyboardInterrupt:
        logger.info("Stopping balloon game producer...")
    except Exception as e:
        logger.error(f"Error in balloon game producer: {str(e)}")
        raise



