import asyncio
from stream import balloon_popper


def main():
    asyncio.run(balloon_popper.run())
