# Blueprint Lab

Blueprint Lab is an offline Factorio blueprint analysis and generation toolkit.
It is not a Factorio runtime mod and must not be placed under any mod `src/`
tree.

## Current Scope

- Decode and encode Factorio blueprint strings.
- Walk blueprint books, blueprints, upgrade planners, and deconstruction planners.
- Measure blueprint boundaries, entity counts, tile counts, density, dominant entities, and simple edge I/O hints.
- Scan a local blueprint corpus and produce JSON or Markdown reports.
- Classify blueprint families and choose representative examples for later template extraction.
- Generate the first rectangular black-box seed blueprint: ore-to-plate with a stable left-input and right-output boundary.

The current generator is a seed for later optimization. It is not yet a full
from-ore-to-final-product Space Age black-box factory generator.

## Knowledge Model

The tool separates three knowledge layers:

- Game knowledge: recipes, items, entity sizes, collision boxes, belt speed, fluid handling, modules, beacons, qualities, and Space Age planet rules.
- Corpus knowledge: patterns extracted from existing blueprint books, including rectangular boundaries, repeated modules, entity density, dominant entities, and I/O hints.
- Strategy knowledge: full-belt targets, module templates, rectangle packing, routing heuristics, scoring functions, and verified generated cases.

This split is deliberate. A blueprint string can carry layout JSON, but it does
not carry the complete recipe/prototype model needed to design a factory. Future
recipe and prototype data should come from official docs and current game or mod
`data.raw` exports instead of hand-written guesses.

## Corpus Findings

The first full scan of `D:\Desktop\游戏\异星工厂\蓝图` decoded 78 text blueprint
files with no failures:

- 389 blueprint books.
- 3230 normal blueprints.
- 151 upgrade planners.
- 44 deconstruction planners.
- 1264522 entities.
- 1724158 tiles.

Early layout lessons:

- Compact black-box production blueprints often become long rectangles rather than squares, because straight belt, pipe, heat, and platform lanes are easier to keep saturated and inspect.
- Dense Space Age platform and science blueprints frequently include many tiles, so entity-only density is misleading; tile count and platform footprint must be part of the score.
- Balancer families are a good controlled generator target because their I/O contract is explicit and the best examples keep belt-like entities on edges.
- Very large integrated factories are better treated as packed groups of smaller repeated modules before attempting end-to-end generation.
- Family learning currently classifies examples into balancer, smelting, science, quality, space-platform, rail, power, mall, circuit, logistics, defense, and other. The rules are intentionally explicit: labels, path text, dominant entity names, density, aspect ratio, and edge belt hints are visible in the report.
- The learning report is not yet a recipe-DAG understanding pass. It identifies families, representative examples, and black-box candidates that should be inspected or decomposed into reusable modules next.

The first family-learning run found these high-signal candidate types:

- Science and Space Age platform boxes: dense long rectangles such as `115k/m`, `620/m[item=promethium-science-pack]`, `传说星岩`, and black-bottle ships. These are the closest examples for the desired end-to-end black-box generator.
- Smelting and ore boxes: repeated furnace/foundry rows and explicit ore/plate labels. These are the bridge between simple module expansion and integrated factories.
- Mall and logistics boxes: useful for input-boundary and requester patterns, but they trade compactness for coverage.
- Balancers and rail modules: valuable as standalone template families, but they should not be mixed into production-box scoring without separate constraints.

## Commands

Analyze a blueprint directory:

```bash
python3 -m tools.blueprint_lab.analysis /mnt/d/Desktop/游戏/异星工厂/蓝图 --json-output .codex/tests/blueprint-corpus-summary.json --markdown-output .codex/tests/blueprint-corpus-report.md
```

Learn blueprint families and representative examples:

```bash
python3 -m tools.blueprint_lab.learn /mnt/d/Desktop/游戏/异星工厂/蓝图 --json-output .codex/tests/blueprint-learning-summary.json --markdown-output .codex/tests/blueprint-learning-report.md
```

Generate the current seed blueprint:

```bash
python3 -m tools.blueprint_lab.generate iron-plate-seed --furnace-pairs 8 --output .codex/tests/iron-plate-blackbox-seed.txt
```

Run the regression guard:

```bash
python3 tests/verify_blueprint_lab.py
```

## Official References

- Blueprint string format: `https://wiki.factorio.com/Blueprint_string_format`
- Runtime blueprint stack APIs: `https://lua-api.factorio.com/latest/classes/LuaItemStack.html`
- Prototype docs and machine-readable prototype format: `https://lua-api.factorio.com/latest/index-prototype.html`
