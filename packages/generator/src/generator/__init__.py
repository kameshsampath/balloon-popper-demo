# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

import asyncio
from stream import balloon_popper


def main():
    asyncio.run(balloon_popper.run())
