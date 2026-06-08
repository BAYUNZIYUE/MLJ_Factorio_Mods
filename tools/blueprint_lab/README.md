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
- Audit connected boundary belt capacity against data.raw belt speed, so generated reports can catch cases where machine coverage is high enough but the final boundary has too few belt lanes.
- Audit production-machine inserter endpoints against data.raw entity boxes, so generated reports can distinguish target machines with belt-fed input/output from copied but disconnected machines.
- Audit target recipes for item byproducts that are not the requested output, including whether a byproduct is also a same-recipe input that should be recycled to the input boundary.
- Insert target-item filter splitters on output routes when a target recipe has item byproducts; the current separator keeps the target item on the main output route and sends byproducts into a non-boundary overflow lane while reporting whether that overflow is only a temporary stand-in for recycling.
- Import a generated blueprint through a real Factorio runtime scenario and attempt to build it on the matching surface type. Space platform blueprints are validated on a temporary space platform with foundation tiles pre-placed before entity building is attempted; if `build_blueprint` returns zero entities, the validator can fall back to direct `surface.create_entity` placement to prove the entity names, qualities, recipe qualities, underground-belt endpoint types, module item stacks, and occupied positions are accepted by the current game runtime.
- The runtime fallback also restores splitter filters and input/output priorities, so future item-separation passes can be validated on platform blueprints that still require direct placement. Runtime boundary audit records right-boundary samples and cleanliness separately, distinguishing a boundary that contains target products from one that also leaks recipe input or byproduct items.
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
estimated rectangle before any connector belts or pipes are generated. The
repeat-grid column chooser scores candidate grids by estimated connector work,
sparse tail cells, and rectangle area. This prefers straight reusable bus rows
when they avoid a nearly empty final row, while still allowing multi-row grids
when they reduce sparse output spans. This matches the corpus lesson that
integrated black boxes usually preserve local module geometry first, then use
long boundary buses to make the final rectangle manageable.

The materializer is the first step that writes a generated blueprint string from
learned corpus templates. It copies normalized entities and tiles into the
planned rectangle, preserves recipe/direction/quality fields and raw entity
`items` stacks that were learned from the source blueprint, preserves blueprint
entity `type` fields such as underground-belt input/output ends, reassigns
entity numbers, and de-duplicates identical tile placements. When data.raw
knowledge is available, it prunes each copied production cell to the layout
node's target recipe: target recipe machines, belt-connected target inserters,
the target inserter belt endpoints, learned boundary-port belt lanes,
beacons/support entities, and tiles are kept, while other recipe machines,
unrelated inserters, and unrelated belt-like lanes are dropped. This keeps the
generated box closer to the selected target instead of copying every recipe and
every bus lane that happened to share the learned grid cell. With
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

When boundary connection is enabled for a single repeated-template node, the
materializer performs a post-materialization column search. It tries the
possible repeated-grid column counts, materializes each candidate, runs the real
connector, flow, capacity, and machine I/O audits, then chooses by audit result
before compactness. The selection prefers no collisions, proven output boundary
capacity, no failed or unresolved belt flow, and a horizontal rectangle before
falling back to area and entity count. This is intentionally later than the
layout-plan estimate: a layout that looks compact can still be worse if its
second full-belt lane depends on an unresolved underground belt, while a
slightly taller multi-row rectangle can expose two proven surface output lanes.

Connector routing reports each boundary as `connected`, `stub-only`, or
`blocked`. A connected route found a compatible learned edge port and added a
collision-free belt line. A stub-only route has no compatible learned port yet.
A blocked route found a port but refused to add partial belts because an exact
entity-position collision was detected. The router evaluates all compatible
ports on the requested side before declaring a route blocked; failed direct
candidates are retained in `blocked_attempts` so the report can explain why a
later port was chosen. When data.raw belt capacity shows that one boundary
route cannot carry the requested rate, the router keeps choosing additional
learned ports on different lanes until the boundary has enough connected belt
capacity or no usable learned lane remains. Connector belts inherit the selected
port belt tier when the port is a transport belt, underground belt, or splitter.
Blueprint Lab uses Factorio 2.x direction values, where cardinal belts use
north `0`, east `4`, south `8`, and west `12`. Learned port roles are
direction-aware evidence, not an absolute route truth: boundary routing first
prefers ports on already connected horizontal bridge lanes, then prefers simple
surface belt lanes, and uses role plus distance as tie breakers. That keeps
full-belt copies on the same learned bus instead of blindly choosing a labeled
port that cannot fan out across repeated instances. Inter-instance bridges are
reported separately from boundary routes so a generated full-belt box can show
whether repeated module edge buses were connected before the final boundary
output was attached. The default bridge pass connects simple surface belt lanes
first; extra learned lanes chosen by multi-belt boundary routing get their own
on-demand bridge pass. The bridge generator does not start a visible horizontal
bridge from an underground-belt `input` end or terminate one at an
underground-belt `output` end, because those are tunnel entrance/exit semantics
rather than ordinary surface belts. Boundary coverage then audits the route plus
bridges as a graph:
output coverage walks backward from the selected output port through connected
instance bridges, while input coverage walks forward from the selected input
port. Coverage is lane-aware: only bridges on the same y coordinate as the
selected boundary port are used for reachability. Repeated template rows are
handled independently, then coverage for the same boundary and template is
aggregated so a multi-row plan can prove that every copied instance is reached.
This lets the report distinguish "the boundary belt touches one copied module"
from "the boundary belt reaches every copied module needed to cover the
requested target rate". Input fanouts extend that same reachability graph for
copied modules on the same row. They add belts only on empty positions and can
treat existing same-tier transport belts, underground belts, or splitters as
already-built bus segments; non-belt collisions still block the fanout.

Boundary capacity audit is separate from boundary coverage. Coverage proves
that connected routes and repeated-instance buses reach the copied machines that
can produce the requested rate. Capacity audit groups connected boundary routes
by boundary and learned template, sums their data.raw belt throughput, and now
uses the belt flow audit before marking that capacity as proven. This matters
for multi-belt targets: a generated box may have enough machines and internal
buses for `2x turbo-transport-belt`, but one connected turbo output lane still
only has 3600 items/minute of boundary capacity. Two connected turbo lanes have
7200 items/minute of structural capacity, but the audit reports `unresolved`
instead of `sufficient` if one lane depends on splitter or underground-belt
semantics that the belt flow audit has not proven. The materializer can add a
second connected boundary route when a second learned lane is available;
underground-backed lanes remain `unresolved` in belt flow audit until a
dedicated underground-pair parser can prove their semantics.

The belt flow audit is a stricter pass over those connected segments. It
rebuilds each horizontal boundary route, inter-instance bridge, and input
fanout from the entities that will actually be exported, then checks that every
occupied position is a same-tier belt-like entity pointing east. A segment is
`pass` when all checked entities are simple direction-compatible belt flow. It
is `failed` when a belt is missing, the tier differs, a non-belt entity occupies
the path, or the direction is wrong. East-facing underground-belt `output` ends
can pass at the start of a visible segment, and east-facing underground-belt
`input` ends can pass at the end of one. A same-segment east-facing
underground-belt `input` followed by a matching `output` can also pass; the
route generator treats the tiles between that pair as hidden tunnel span instead
of filling them with visible connector belts. Underground endpoints that do not
form such an explicit input-to-output pair, underground belts without a
preserved type, overlong pairs beyond the data.raw `max_distance`, and
splitters stay `unresolved` until a stronger parser can prove their semantics. The current exception is an east-facing target-output filter splitter with `output_priority=left`; this is accepted as proven for the target output route because a runtime splitter probe confirmed that the filtered item stays on the main route while non-target items leave on the side output.
This is still not a full belt simulation: it does not understand lane filters,
splitter balancing, stacked belts, cross-segment underground-belt pairing, or
inserter timing.

The machine I/O audit is the next conservative semantic pass. It imports
entity selection boxes and inserter pickup/insert positions from the current
data.raw export, rotates inserter endpoint vectors by blueprint direction, and
checks whether each recipe machine has at least one belt-to-machine input
inserter and one machine-to-belt output inserter when the recipe has item inputs
and products. This is weaker than a Factorio simulation: it does not prove
inserter throughput, stack size, filters, lane choice, item identity, or whether
unrelated recipe machines copied from the learned cell should remain in the
generated target box. It is still useful because it exposes when a learned
template copies extra recipe machines that are not attached to the selected
target bus.

The runtime validation command is a heavier final gate, not part of the normal
unit regression guard. It writes a temporary scenario under the Factorio user
data directory, imports one blueprint string with `LuaItemStack.import_stack`,
creates a generic surface or a Space Age space platform depending on blueprint
tiles, and calls `LuaItemStack.build_blueprint`. If that returns zero entities,
the command falls back to direct `LuaSurface.create_entity` placement. This
fallback is not the same as proving that the exported blueprint can be built
with one Factorio blueprint action; it proves that the current runtime accepts
the generated entities, qualities, recipe qualities, underground-belt endpoint
types, module item stacks, platform tiles, and occupied positions. The current
generated platform blueprint reaches that fallback: `import_stack=0`,
`built_entities=0`, `manual_entities=436`, `manual_failures=0`,
`manual_recipe_set=5`, `manual_recipe_failures=0`,
`manual_underground_types=25`, `manual_underground_type_failures=0`,
`manual_modules_inserted=30`, and `manual_module_failures=0`. After unlocking
all recipes and technologies and waiting 120 ticks, the same run reports five
`metallic-asteroid-crushing` machines with positive crafting speed, module
items installed, and electric network connection. Their current status is
`item_ingredient_shortage`, so the next validation boundary is external
asteroid-chunk input flow rather than placement, recipe unlock, module, or
power availability.

The runtime validator now includes a first input-flow probe. It collects item
ingredients from recipe machines, force-inserts those items onto east-facing
transport lines near the left edge of the built surface, waits for the same
runtime audit tick, then counts both recipe input items and recipe products on
all transport lines. This is deliberately a diagnostic probe rather than a
success criterion. In the current platform sample, inserting
`metallic-asteroid-chunk` onto left-edge belts leaves the crushers in
`item_ingredient_shortage` and the transport audit sees chunks but no
`iron-ore`: the boundary-looking input lanes are not the machine pickup lanes.
The validator therefore also tries a stricter probe: for each recipe machine,
it finds inserters that drop into that machine, locates the belt entity under
the inserter pickup position, and force-inserts the recipe input there. The
latest runtime probe found 5 such input inserters and 5 pickup belts; after 5
pickup-lane insertions, the audit reported `products_finished=7`,
`output_items=100`, and transport-line items `iron-ore:35` plus
`metallic-asteroid-chunk:400`. That proves the copied crusher cell can run when
fed at the real pickup lane. The next generator problem is to make the external
boundary route and input fanout connect to those proven pickup lanes instead of
only to a learned left-edge bus.

The materializer now promotes machine input pickup belts and machine output
drop belts into routeable `machine-input` / `machine-output` ports. For vertical
pickup lanes, it can generate a left-boundary route into the real pickup belt
instead of pretending that a horizontal edge bus reaches the machine. For output
ports, route scoring prefers the actual drop lane over the topmost adjacent lane
when both are structurally available. The current `iron-ore` 2x turbo full-belt
sample selects a 4x2 copied-crusher grid with five machine-input routes and two
right-side `turbo-transport-belt` output routes.

Full-belt targets carry a boundary-contract audit. For a target such as `2x
turbo-transport-belt`, the audit expects exactly two connected output routes
using `turbo-transport-belt`; the current `iron-ore` 2x turbo sample reports
`exact` with lanes `[8.5, 36.0]`. The same sample now also detects that
`metallic-asteroid-crushing` can return `metallic-asteroid-chunk` as a 0.2
probability item byproduct. The materializer inserts two target-item filter
splitters, keeps `iron-ore` on the main output routes, and recognizes that the
byproduct chunk is also the recipe input. The current generated geometry routes
those side outputs back to the left input boundary with U-shaped recycle-return
belts when a collision-free lane is available; otherwise it falls back to a
finite non-boundary overflow lane and reports that fallback explicitly.

For the current `iron-ore` 2x turbo sample, both output separations are
`recycle-merge-to-input-boundary`. The report shows zero overflow belts, 119
recycle/merge belts, and per-route `recycle_flow=pass` audits over 93 and 26
checked belt positions. The merge targets are side-loads into the existing
left-side `metallic-asteroid-chunk` input lanes at `(0.5,23.5)` and `(0.5,38.0)`.

Left-only runtime probes against the current recycle-merge blueprint import 717
entities, place them through the direct-placement fallback, insert
`metallic-asteroid-chunk` only on left-edge transport lines, and restore splitter
filters/priorities with zero splitter-setting failures. A 2400-tick runtime audit
reports `right_boundary_cleanliness status=clean` with `iron-ore` on the right
boundary and no input/byproduct items there. The same probe still observes some
`metallic-asteroid-chunk` on internal transport lines, so this proves the audited
right output boundary is clean for the tested window, not that the internal
recycle loop is fully drained or long-run stable. It also still does not prove
sustained full-belt throughput or player `build_blueprint` success on a platform
surface.

The runtime validator can also repeat the left-boundary input injection before
the final audit with `--sustained-input-interval-ticks`. This is a stronger
runtime stress probe than a single initial injection because it keeps feeding
the copied boundary during the audit window, while still remaining a diagnostic
input source rather than a real throughput meter. In the current `iron-ore 2x
turbo-transport-belt` recycle-merge sample, a 2400-tick probe with a 300-tick
interval reports `sustained_input_injection interval_ticks=300 cycles=7
inserted=308 failures=0`, five crushers at `status=full_output`, `iron-ore`
reaching the right boundary, and `right_boundary_cleanliness status=clean`.
Internal `metallic-asteroid-chunk` remains visible on transport lines, so the
result should be read as "right boundary stayed clean under periodic test
feeding for this window", not as sustained full-belt or infinite-stability
proof.

For throughput-style validation, the runtime validator can run a right-boundary
window drain with `--throughput-window-ticks` and `--throughput-target-item`.
The implementation follows the same rightmost transport-line boundary used by
the cleanliness audit, drains tracked items from that boundary every tick with
`LuaTransportLine.remove_item`, and aggregates the removed counts into
`--throughput-window-ticks` report windows. This measures whole-boundary
delivered items rather than half-lane balancing, which matches the current
generator goal better than lane-perfect accounting. It is still a diagnostic
sink: removing items from the right boundary prevents output backup during the
probe, so the result is evidence for delivered product rate under a test sink,
not a complete proof of natural steady-state full-belt throughput.
In the current `iron-ore 2x turbo-transport-belt` recycle-merge sample, the
300-tick throughput windows after startup report about `444-456/min` delivered
`iron-ore`, while the requested contract is `7200/min`. That is useful negative
evidence: the generated box now has clean output and repeated runtime delivery,
but it is still far from a sustained 2x turbo full-belt output.

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

Validate one generated blueprint with a real Factorio runtime scenario:

```bash
python3 -m tools.blueprint_lab.factorio_validate --blueprint .codex/tests/blueprint-connected-iron-ore.txt --mod-directory /mnt/c/Users/MLJ/AppData/Roaming/Factorio/mods --console-log .codex/tests/blueprint-lab-factorio-validation.log
```

Run a longer sustained left-boundary input probe:

```bash
python3 -m tools.blueprint_lab.factorio_validate --scenario-name blueprint_lab_validation_recycle_merge_sustained_2400 --blueprint .codex/tests/blueprint-routed-iron-ore-2x-turbo-belt.txt --user-data-dir .codex/tests/factorio-probe-write-data --mod-directory /mnt/c/Users/MLJ/AppData/Roaming/Factorio/mods --console-log .codex/tests/blueprint-lab-factorio-recycle-merge-sustained-2400.log --until-tick 2400 --timeout-seconds 120 --input-probe left --runtime-audit-wait-ticks 2400 --sustained-input-interval-ticks 300
```

Run a right-boundary throughput-window probe:

```bash
python3 -m tools.blueprint_lab.factorio_validate --scenario-name blueprint_lab_validation_recycle_merge_throughput_2400 --blueprint .codex/tests/blueprint-routed-iron-ore-2x-turbo-belt.txt --user-data-dir .codex/tests/factorio-probe-write-data --mod-directory /mnt/c/Users/MLJ/AppData/Roaming/Factorio/mods --console-log .codex/tests/blueprint-lab-factorio-recycle-merge-throughput-2400.log --until-tick 2400 --timeout-seconds 120 --input-probe left --runtime-audit-wait-ticks 2400 --sustained-input-interval-ticks 300 --throughput-window-ticks 300 --throughput-target-item iron-ore
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
- Runtime transport-line APIs: `https://lua-api.factorio.com/latest/classes/LuaTransportLine.html`
- Direction type: `https://lua-api.factorio.com/latest/types/Direction.html`
- Prototype docs and machine-readable prototype format: `https://lua-api.factorio.com/latest/index-prototype.html`
- Transport belt connectable prototype speed: `https://lua-api.factorio.com/latest/prototypes/TransportBeltConnectablePrototype.html`
