from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeSource:
    name: str
    url: str
    use: str


OFFICIAL_SOURCES = [
    KnowledgeSource(
        name="Blueprint string format",
        url="https://wiki.factorio.com/Blueprint_string_format",
        use="Decode and encode offline blueprint JSON wrappers.",
    ),
    KnowledgeSource(
        name="LuaItemStack runtime blueprint APIs",
        url="https://lua-api.factorio.com/latest/classes/LuaItemStack.html",
        use="Cross-check in-game blueprint entity/tile mutation capabilities.",
    ),
    KnowledgeSource(
        name="Prototype docs machine-readable format",
        url="https://lua-api.factorio.com/latest/index-prototype.html",
        use="Seed future data.raw/prototype knowledge import instead of hard-coding recipes.",
    ),
]


KNOWLEDGE_LAYERS = {
    "game": [
        "recipes",
        "items",
        "entity sizes and collision boxes",
        "belts and underground reach",
        "fluids",
        "modules and beacons",
        "qualities",
        "Space Age planet constraints",
    ],
    "corpus": [
        "blueprint families",
        "rectangular boundaries",
        "repeated modules",
        "edge I/O hints",
        "density and area metrics",
        "dominant entity patterns",
    ],
    "strategy": [
        "full-belt targets",
        "module templates",
        "rectangle packing",
        "routing heuristics",
        "scoring functions",
        "verified generated cases",
    ],
}

