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
- Derive full-belt target rates from data.raw belt prototypes, so a generator run can request `1x turbo-transport-belt` instead of hand-writing `3600/min`.
- Plan a production DAG seed from learned production templates: target item rate, whole-template instance counts, upstream template needs, and external black-box inputs.
- Turn a production DAG seed into a rectangular layout plan with repeated template grids, estimated module dimensions, and left/right black-box boundaries.
- Materialize a layout plan into an importable blueprint skeleton by copying learned normalized template entities and tiles into the planned rectangle.
- Connect same-row copied input ports with a conservative fanout pass that can reuse existing same-tier belt, underground-belt, and splitter entities as bus evidence instead of overwriting them.
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
items. It reports both `base_without_modules` and `effective_direct_modules`.
The effective rate applies machine quality, direct module stacks learned from
the source entity, and conservative same-template beacon effects. Positive
module effects are scaled by module quality. Cross-template beacon effects are
still not applied. Observed `occurrence_count` is kept separate so later DAG
planning can decide how many template instances to place.

Full-belt targets are also data.raw driven. The knowledge layer imports
transport belt, underground belt, and splitter `speed` prototypes and calculates
the unstacked belt rate as `speed * 480` items per second. With the current
Space Age data.raw, that gives normal / fast / express / turbo rates of 15, 30,
45, and 60 items per second, or 900, 1800, 2700, and 3600 items per minute.
This is why the full-belt CLI accepts `--target-belt turbo-transport-belt`
instead of relying on a hard-coded item rate.

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
in-game validation. The DAG uses the strongest available rate basis in this
order: `effective_with_beacons`, `effective_direct_modules`, then
`base_without_modules`.

The layout plan converts DAG nodes into conservative rectangular units. It
keeps each learned template as the copyable atom, arranges repeated instances in
rows, reserves a left input boundary and right output boundary, and reports the
estimated rectangle before any connector belts or pipes are generated. This
matches the corpus lesson that integrated black boxes usually preserve local
module geometry first, then use long boundary buses to make the final rectangle
manageable.

The materializer is the first step that writes a generated blueprint string from
learned corpus templates. It copies normalized entities and tiles into the
planned rectangle, preserves recipe/direction/quality fields and raw entity
`items` stacks that were learned from the source blueprint, preserves blueprint
entity `type` fields such as underground-belt input/output ends, reassigns
entity numbers, and de-duplicates identical tile placements. With
`--connect-boundaries`, it also adds conservative transport-belt stubs in the
reserved left/right lanes and reports exact entity-position collisions. It
also bridges same-row adjacent repeated template instances when their learned
left/right edge-bus ports share the same y coordinate. This mirrors the corpus
pattern that copy-expanded modules become useful only when their edge buses are
stitched across the gaps between repeated cells. It intentionally does not
generate full internal belt routing, pipes, power, missing modules,
cross-template beacon effects, or collision repairs yet; those must be separate
passes so they can be validated instead of hidden in the first generated
skeleton.

Connector routing reports each boundary as `connected`, `stub-only`, or
`blocked`. A connected route found a compatible learned edge port and added a
collision-free belt line. A stub-only route has no compatible learned port yet.
A blocked route found a port but refused to add partial belts because an exact
entity-position collision was detected. The router evaluates all compatible
ports on the requested side before declaring a route blocked; failed direct
candidates are retained in `blocked_attempts` so the report can explain why a
later port was chosen. Connector belts inherit the selected port belt tier when
the port is a transport belt, underground belt, or splitter. Blueprint Lab uses
Factorio 2.x direction values, where cardinal belts use north `0`, east `4`,
south `8`, and west `12`. Learned port roles are direction-aware: for example,
a left-edge east-facing belt is an input, while a left-edge west-facing belt is
an output. Inter-instance bridges are reported separately from boundary routes
so a generated full-belt box can show whether repeated module edge buses were
connected before the final boundary output was attached. The bridge generator
does not start a visible horizontal bridge from an underground-belt `input` end
or terminate one at an underground-belt `output` end, because those are tunnel
entrance/exit semantics rather than ordinary surface belts. Boundary coverage
then audits the route plus bridges as a graph: output coverage walks backward
from the selected output port through connected instance bridges, while input
coverage walks forward from the selected input port. Coverage is lane-aware:
only bridges on the same y coordinate as the selected boundary port are used for
reachability. This lets the report distinguish "the boundary belt touches one
copied module" from "the boundary belt reaches every copied module needed to
cover the requested target rate". Input fanouts extend that same reachability
graph for copied modules on the same row. They add belts only on empty positions
and can treat existing same-tier transport belts, underground belts, or
splitters as already-built bus segments; non-belt collisions still block the
fanout.

The belt flow audit is a stricter pass over those connected segments. It
rebuilds each horizontal boundary route, inter-instance bridge, and input
fanout from the entities that will actually be exported, then checks that every
occupied position is a same-tier belt-like entity pointing east. A segment is
`pass` when all checked entities are simple direction-compatible belt flow. It
is `failed` when a belt is missing, the tier differs, a non-belt entity occupies
the path, or the direction is wrong. East-facing underground-belt `output` ends
can pass at the start of a visible segment, and east-facing underground-belt
`input` ends can pass at the end of one. Underground belts in the middle of a
visible segment, underground belts without a preserved type, and splitters stay
`unresolved` until a dedicated pairing or splitter parser can prove their
semantics. This is still not a full belt simulation: it does not understand lane
filters, splitter balancing, stacked belts, underground-belt pairing semantics,
or inserter timing.

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

Use a full-belt target instead of a hand-written rate:

```bash
python3 -m tools.blueprint_lab.production_dag /mnt/d/Desktop/游戏/异星工厂/蓝图 --data-raw-json /path/to/data-raw.json --target-item iron-ore --target-belt turbo-transport-belt --target-belt-count 1 --top 8 --cell-size 16
```

Plan a rectangular layout from learned templates:

```bash
python3 -m tools.blueprint_lab.layout_plan /mnt/d/Desktop/游戏/异星工厂/蓝图 --data-raw-json /path/to/data-raw.json --target-item iron-ore --target-belt turbo-transport-belt --top 8 --cell-size 16 --json-output .codex/tests/blueprint-layout-plan-summary.json --markdown-output .codex/tests/blueprint-layout-plan-report.md
```

Materialize a blueprint skeleton from learned templates:

```bash
python3 -m tools.blueprint_lab.materialize /mnt/d/Desktop/游戏/异星工厂/蓝图 --data-raw-json /path/to/data-raw.json --target-item iron-ore --target-belt turbo-transport-belt --top 8 --cell-size 16 --connect-boundaries --output .codex/tests/blueprint-connected-iron-ore.txt --json-output .codex/tests/blueprint-connected-iron-ore-summary.json --markdown-output .codex/tests/blueprint-connected-iron-ore-report.md
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
- Direction type: `https://lua-api.factorio.com/latest/types/Direction.html`
- Prototype docs and machine-readable prototype format: `https://lua-api.factorio.com/latest/index-prototype.html`
- Transport belt connectable prototype speed: `https://lua-api.factorio.com/latest/prototypes/TransportBeltConnectablePrototype.html`
