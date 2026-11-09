import os.path
import typing
from dataclasses import dataclass
import logging
import sys

# set a logger for debugging and by default write to stdout. The logger will be used to print the events of the elevator simulation.

IS_DEBUG_MODE = os.path.exists("test.in")
log_level = logging.INFO if IS_DEBUG_MODE else logging.CRITICAL
logging.basicConfig(stream=sys.stderr, level=log_level)
logger = logging.getLogger(__name__)

# Declare two directions for the elevator: UP and DOWN. Use an IntEnum for clarity.
from enum import IntEnum
class Direction(IntEnum):
    UP = 1
    DOWN = -1

class EventType(IntEnum):
    PICKUP = 1
    DROPOFF = 2


@dataclass
class ElevatorEvent:
    type: EventType
    floor: int
    person_index: int

def __main__():
    logger.log(logging.INFO, "Starting elevator simulation")

    # sys.stdin = open("test.in", encoding="utf-8", mode='r')  # redirect stdin to a file for easier testing
    #sys.stdout= open("test.out", encoding="utf-8, mode='w'")  # redirect stdout to a file for easier reading of the output

    data = list(map(int, sys.stdin.read().split()))
    data_iter = iter(data)

    n = next(data_iter)
    m = next(data_iter)

    s_i  = [next(data_iter) for _ in range(m)]
    t_i  = [next(data_iter) for _ in range(m)]

    #print(f"n={n}, m={m}, s_i={s_i}, t_i={t_i}")

    # Create two lists Q1 and Q2. We'll record the pickup and dropoff events in these lists. Each event contains the type the floor and the person index.
    # Q1 contains the persons for each i in range(m) where s_i[i] < t_i[i].
    # Q2 contains the persons for each i in range(m) where s_i[i] >= t_i[i].

    Q1 = []
    Q2 = []
    q1_idx = 0
    q2_idx = 0
    for i in range(m):
        if s_i[i] < t_i[i]:
            Q1.append(ElevatorEvent(EventType.PICKUP, s_i[i], i))
            Q1.append(ElevatorEvent(EventType.DROPOFF, t_i[i], i))
        elif s_i[i] > t_i[i]: # otherwise, ignore.
            Q2.append(ElevatorEvent(EventType.PICKUP, s_i[i], i))
            Q2.append(ElevatorEvent(EventType.DROPOFF, t_i[i], i))

    # Now sort all events in Q1 and Q2 by floor. For Q1, we want to sort by floor ascending, and for Q2, we want to sort by floor descending.
    Q1.sort(key = lambda x: x.floor)
    Q2.sort(key = lambda x: -x.floor)

    # Now simulate the elevator process
    current_floor = -1
    direction = Direction.UP
    num_stops = 0
    capacity = m + 1

    def log_event(event: ElevatorEvent, prefix_custom: str = None):
        logger.log(logging.INFO, f"{prefix_custom if prefix_custom else "Stopping at floor"}  {event.floor} "
                                 f"for person {event.person_index} ({'pickup' if event.type == EventType.PICKUP else 'dropoff'})")

    def is_end_of_Q1():
        return q1_idx >= len(Q1)

    def is_end_of_Q2():
        return q2_idx >= len(Q2)

    while not is_end_of_Q1() or not is_end_of_Q2():
        if direction == Direction.UP:
            # Process Q1 until we reach the top floor or Q1 is empty
            if not is_end_of_Q1():
                while not is_end_of_Q1():
                    next_stop_up = Q1[q1_idx]; q1_idx += 1
                    if current_floor != next_stop_up.floor:
                        num_stops += 1
                        current_floor = next_stop_up.floor
                        log_event(next_stop_up)
                    else: # We are already at the next stop, so we can just log it
                        log_event(next_stop_up, prefix_custom="Already at floor! - ")

                # If reached the top floor, we need to switch direction to DOWN and process Q2.
                if current_floor == n - 1:
                    direction = Direction.DOWN
            else:
                # If Q1 is empty, or we are at the top floor, we need to switch direction to DOWN and process Q2.
                direction = Direction.DOWN
        else:
            # Process Q2
            if not is_end_of_Q2():
                # First, if the elevator is not at the top floor, we need to move it to the top floor before processing Q2.
                # if current_floor != n - 1:
                #     current_floor = n - 1
                #     logger.log(logging.INFO, f"Moving elevator to top floor {current_floor} before processing Q2")
                #     #num_stops += 1 # THey don't want to count this

                # Take all the event in Q2 and process them in order.
                # Since Q2 is sorted in descending order, we can just pop the first event and process it.
                while not is_end_of_Q2():
                    next_stop_down = Q2[q2_idx]; q2_idx += 1
                    if current_floor != next_stop_down.floor:
                        current_floor = next_stop_down.floor
                        num_stops += 1
                        log_event(next_stop_down)
                    else:
                        log_event(next_stop_down, prefix_custom="Already at floor! - ")

    logger.log(logging.INFO, f"Total number of stops: {num_stops}")
    print(num_stops)

__main__()
