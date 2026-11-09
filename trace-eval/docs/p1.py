import typing
from dataclasses import dataclass

global n, m, s_i, t_i

def set_test1():
    global n, m, s_i, t_i
    n = 10
    m = 3
    s_i = [0, 4, 4]
    t_i = [4, 2, 9]

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
    set_test1()
    #print(f"n={n}, m={m}, s_i={s_i}, t_i={t_i}")

    # Create two lists Q1 and Q2. We'll record the pickup and dropoff events in these lists. Each event contains the type the floor and the person index.
    # Q1 contains the persons for each i in range(m) where s_i[i] < t_i[i].
    # Q2 contains the persons for each i in range(m) where s_i[i] >= t_i[i].

    Q1 : list[ElevatorEvent] = []
    Q2 : list[ElevatorEvent] = []
    for i in range(m):
        if s_i[i] < t_i[i]:
            Q1.append(ElevatorEvent(EventType.PICKUP, s_i[i], i))
            Q1.append(ElevatorEvent(EventType.DROPOFF, t_i[i], i))
        else:
            Q2.append(ElevatorEvent(EventType.PICKUP, s_i[i], i))
            Q2.append(ElevatorEvent(EventType.DROPOFF, t_i[i], i))

    # Now sort all events in Q1 and Q2 by floor. For Q1, we want to sort by floor ascending, and for Q2, we want to sort by floor descending.
    Q1.sort(key = lambda x: x.floor)
    Q2.sort(key = lambda x: -x.floor)

    # Now simulate the elevator process
    current_floor = 0
    direction = Direction.UP
    num_stops = 0
    while Q1 or Q2:
        if direction == Direction.UP:
            # Process Q1
            # Remove the first element from Q1 and set the current floor to its target floor.
            if Q1:
                next_stop = Q1.pop(0)

        else:
            # Process Q2
            pass


__main__()
