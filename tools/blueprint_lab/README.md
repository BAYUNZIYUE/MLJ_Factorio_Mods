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
- Decompose learned black-box candidates into boundary ports, coarse grid signatures, and repeated module candidates.
- Extract normalized entity subgraph templates from repeated grid signatures.
- Import data.raw JSON and map recipe-bearing templates to recipe inputs, outputs, machine names, base machine speeds, conservative per-template-instance throughput, modules, and requests.
- Plan a production DAG seed from learned production templates: target item rate, whole-template instance counts, upstream template needs, and external black-box inputs.
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

The first decomposition pass adds a second evidence layer for black-box
candidates:

- Boundary ports show where belts, fluid endpoints, rail-like entities, and logistics storage touch the rectangle.
- Grid signatures group nearby entity families into coarse cells so repeated cells can be inspected as possible modules.
- Decomposition lessons are intentionally conservative. A repeated cell is not automatically a recipe module; it is a candidate for later extraction and in-game validation.

The first template extraction pass turns repeated grid cells into normalized
entity subgraphs:

- Each template records a fingerprint, normalized entities, entity families, recipes, module/request items, and control/connection clues.
- Recipe-bearing templates are stronger generation material than route-only or platform-fill templates.
- Template candidates are still evidence, not proof. They need recipe data and in-game validation before becoming production modules.

The prototype knowledge layer accepts a current game or mod `data.raw` JSON
export. Without that export, recipe-bearing templates remain unresolved by
design; with it, the report can show recipe category, craft time, ingredients,
products, machine names, base machine speeds, conservative input/output rates
per minute for one normalized template instance, module items, and request
items. The current throughput estimate is deliberately conservative: it uses
only recipe time and machine crafting speed, and records modules or beacons as
evidence without applying their effects yet. Observed `occurrence_count` is kept
separate so later DAG planning can decide how many template instances to place.

The production DAG seed uses those per-template rates to choose copyable
production units, round them up to whole instances, and recursively expose
upstream needs. Inputs with no learned production template become external
black-box boundary inputs. This mirrors how strong corpus blueprints are built:
repeat proven local modules, then define the box boundary around whatever the
current module library cannot yet produce internally. Common raw inputs such as
ore, stone, coal, water, crude oil, and asteroid chunks are treated as default
boundary inputs for child nodes; pass `--external-item` to add more boundary
items or `--no-default-boundary-items` to inspect deeper recursive chains. It
still does not solve rectangle packing, belt routing, pipe routing, power, or
in-game validation.

## Commands

Analyze a blueprint directory:

```bash
python3 -m tools.blueprint_lab.analysis /mnt/d/Desktop/游戏/异星工厂/蓝图 --json-output .codex/tests/blueprint-corpus-summary.json --markdown-output .codex/tests/blueprint-corpus-report.md
```

Learn blueprint families and representative examples:

```bash
python3 -m tools.blueprint_lab.learn /mnt/d/Desktop/游戏/异星工厂/蓝图 --json-output .codex/tests/blueprint-learning-summary.json --markdown-output .codex/tests/blueprint-learning-report.md
```

Decompose learned black-box candidates:

```bash
python3 -m tools.blueprint_lab.decompose /mnt/d/Desktop/游戏/异星工厂/蓝图 --top 8 --cell-size 16 --json-output .codex/tests/blueprint-decomposition-summary.json --markdown-output .codex/tests/blueprint-decomposition-report.md
```

Extract template candidates:

```bash
python3 -m tools.blueprint_lab.templates /mnt/d/Desktop/游戏/异星工厂/蓝图 --top 8 --cell-size 16 --json-output .codex/tests/blueprint-template-summary.json --markdown-output .codex/tests/blueprint-template-report.md
```

Map templates to data.raw recipe knowledge:

```bash
python3 -m tools.blueprint_lab.template_knowledge /mnt/d/Desktop/游戏/异星工厂/蓝图 --data-raw-json /path/to/data-raw.json --top 8 --cell-size 16 --json-output .codex/tests/blueprint-template-knowledge-summary.json --markdown-output .codex/tests/blueprint-template-knowledge-report.md
```

If no `--data-raw-json` is provided, the command still reports template roles
and unresolved recipes:

```bash
python3 -m tools.blueprint_lab.template_knowledge /mnt/d/Desktop/游戏/异星工厂/蓝图 --top 8 --cell-size 16
```

Plan a production DAG seed from learned templates:

```bash
python3 -m tools.blueprint_lab.production_dag /mnt/d/Desktop/游戏/异星工厂/蓝图 --data-raw-json /path/to/data-raw.json --target-item iron-ore --target-rate-per-minute 600 --top 8 --cell-size 16 --json-output .codex/tests/blueprint-production-dag-summary.json --markdown-output .codex/tests/blueprint-production-dag-report.md
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
