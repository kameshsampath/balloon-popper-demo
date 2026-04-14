# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Shared balloon pop simulation (Kafka producer and bronze batch loader)."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from common.stream.models import GAME_CONFIG, GameEvent


class BalloonGameGenerator:
    """Same rules as the streaming Kafka producer; supports injected RNG and timestamps."""

    def __init__(
        self,
        bonus_probability: float | None = None,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng if rng is not None else random.Random()
        self.bonus_probability = (
            float(bonus_probability)
            if bonus_probability is not None
            else float(GAME_CONFIG.bonus_probability)
        )
        self.cartoon_characters = list(GAME_CONFIG.character_favorites.keys())
        self.balloon_colors = list(GAME_CONFIG.colors.keys())

    def generate_pop(
        self,
        player_name: str,
        *,
        event_ts: datetime | None = None,
    ) -> GameEvent:
        player_character = self._rng.choice(self.cartoon_characters)

        if self._rng.random() < self.bonus_probability:
            balloon_color = self._rng.choice(
                GAME_CONFIG.character_favorites[player_character]
            )
        else:
            balloon_color = self._rng.choice(self.balloon_colors)

        is_favorite_hit = balloon_color in GAME_CONFIG.character_favorites.get(
            player_character, []
        )

        score = GAME_CONFIG.colors.get(balloon_color, 0)
        if is_favorite_hit:
            score = score * 2

        if event_ts is None:
            ts = datetime.now(timezone.utc)
        else:
            ts = event_ts
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

        return GameEvent(
            player=player_name,
            balloon_color=balloon_color,
            score=score,
            favorite_color_bonus=is_favorite_hit,
            event_ts=ts.isoformat().replace("+00:00", "Z"),
        )
