import os.path
import typing
from dataclasses import dataclass
import logging
import sys

# Keep local diagnostics on stderr, separate from the answer.

IS_DEBUG_MODE = os.path.exists("test.in")
log_level = logging.INFO if IS_DEBUG_MODE else logging.CRITICAL
logging.basicConfig(stream=sys.stderr, level=log_level)
logger = logging.getLogger(__name__)


def log_memory(stage: str) -> None:
    if not IS_DEBUG_MODE:
        return

    import psutil

    memory = psutil.Process().memory_info()
    logger.info(
        "[memory] %s: RSS=%.2f MiB, peak RSS=%.2f MiB",
        stage,
        memory.rss / (1024 * 1024),
        memory.peak_wset / (1024 * 1024),

    )


# Declare two directions for the elevator: UP and DOWN. Use an IntEnum for clarity.
from enum import IntEnum
class Direction(IntEnum):
    UP = 1
    DOWN = -1

def __main__():
    logger.log(logging.INFO, "Starting elevator simulation")
    log_memory("before reading input")

    if IS_DEBUG_MODE:
        sys.stdin = open("test.in", encoding="utf-8", mode='r')  # redirect stdin to a file for easier testing
    #sys.stdout= open("test.out", encoding="utf-8, mode='w'")  # redirect stdout to a file for easier reading of the output

    data = list(map(int, sys.stdin.read().split()))
    log_memory("after reading all integers")
    data_iter = iter(data)

    n = next(data_iter)
    m = next(data_iter)

    s_i  = [next(data_iter) for _ in range(m)]
    t_i  = [next(data_iter) for _ in range(m)]

    del data_iter, data # free memory
    log_memory("after building the floor lists")

    #print(f"n={n}, m={m}, s_i={s_i}, t_i={t_i}")

    # Create two byte arrays to hold the events for going up and going down.
    up_events : bytearray = bytearray(n)
    down_events : bytearray = bytearray(n)

    for i in range(m):
        if s_i[i] < t_i[i]:
            up_events[s_i[i]] = 1
            up_events[t_i[i]] = 1
        elif s_i[i] > t_i[i]: # otherwise, ignore.
            down_events[s_i[i]] = 1
            down_events[t_i[i]] = 1

    del s_i, t_i # free memory
    log_memory("after building the event queues")

    # The bytearrays ensure that at each different floor we have 1, we sum them up to get the total number of stops.
    num_stops = sum(up_events) + sum(down_events)

    # Special case: if the elevator drops people at N-1 (top floor), and persons are waiting at floor N-1 to go down,
    # we subtract one stop, because the elevator will not stop again at N-1 to pick them up.
    if up_events[n-1] and down_events[n-1]:
        num_stops -= 1

    log_memory("after simulation")

    logger.log(logging.INFO, f"Total number of stops: {num_stops}")
    print(num_stops)

__main__()
