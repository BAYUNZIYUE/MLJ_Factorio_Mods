from __future__ import annotations


DIR_NORTH = 0
DIR_EAST = 4
DIR_SOUTH = 8
DIR_WEST = 12

DIRECTION_NAMES = {
    DIR_NORTH: "north",
    1: "north-north-east",
    2: "north-east",
    3: "east-north-east",
    DIR_EAST: "east",
    5: "east-south-east",
    6: "south-east",
    7: "south-south-east",
    DIR_SOUTH: "south",
    9: "south-south-west",
    10: "south-west",
    11: "west-south-west",
    DIR_WEST: "west",
    13: "west-north-west",
    14: "north-west",
    15: "north-north-west",
}


def direction_name(direction: int | None) -> str:
    if direction is None:
        return "none"
    return DIRECTION_NAMES.get(direction, str(direction))


def belt_boundary_role(side: str, direction: int | None) -> str:
    if direction is None:
        return "boundary"
    if side == "left" and direction == DIR_EAST:
        return "input"
    if side == "left" and direction == DIR_WEST:
        return "output"
    if side == "right" and direction == DIR_WEST:
        return "input"
    if side == "right" and direction == DIR_EAST:
        return "output"
    if side == "top" and direction == DIR_SOUTH:
        return "input"
    if side == "top" and direction == DIR_NORTH:
        return "output"
    if side == "bottom" and direction == DIR_NORTH:
        return "input"
    if side == "bottom" and direction == DIR_SOUTH:
        return "output"
    return "edge-bus"
