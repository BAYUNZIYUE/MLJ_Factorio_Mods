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
- Upgrade target recipe machine-to-belt output inserters to the strongest same-geometry inserter known in data.raw, preferring `stack-inserter` over `bulk-inserter` when both are available.
- Audit per-output-lane planned load after fan-in reachability, so reports can catch cases where total boundary capacity is sufficient but one lane is overloaded while another lane is underused.
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
on every repeated row, not only the first row; extra learned lanes chosen by
multi-belt boundary routing get their own on-demand bridge pass. The bridge
generator does not start a visible horizontal
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
and products. For machine endpoint matching it rejects corner-only contact,
because the current Space Age crusher template had a copied inserter whose
endpoint touched the target machine's selection-box corner but was not a real
runtime pickup from that machine. This is weaker than a Factorio simulation: it
does not prove inserter throughput, stack size, filters, lane choice, item
identity, or whether unrelated recipe machines copied from the learned cell
should remain in the generated target box. It is still useful because it
exposes when a learned template copies extra recipe machines that are not
attached to the selected target bus.

When data.raw contains stronger inserters with the same pickup and insert
geometry, the materializer upgrades target recipe output inserters after pruning
the learned template. The current policy skips inserters that are already
`bulk-inserter` or `stack-inserter`, then prefers `stack-inserter` and falls
back to `bulk-inserter`. This pass intentionally upgrades only inserters that
pick up from the selected recipe machine and drop to a belt, so input inserters
and unrelated copied machinery are not changed.

Output lane load audit is separate from total boundary capacity. It walks the
same output fan-in graph used by boundary coverage, computes how many copied
instances feed each connected output lane, and compares the planned per-lane
rate with that lane's data.raw belt capacity. In the current `iron-ore 2x
turbo-transport-belt` sample, total output boundary capacity is exactly two
turbo lanes, but the lane load audit reports `y=8.5` as overloaded:
instances `[0, 1, 2, 3]` produce a planned `6300/min` into a `3600/min` lane,
while `y=36.0` carries only instance `[4]` at `1575/min`. This explains why
future layout optimization must balance copied modules across output lanes
instead of only counting the final number of boundary belts.

Runtime probes showed an important limitation of learned `output` edge-bus
ports: a belt lane can be connected and pass the offline belt-flow audit without
actually carrying the target recipe product. A 3x2 candidate connected two
ordinary `output` edge-bus lanes and looked better offline, but the 2400-tick
runtime throughput probe delivered `0/min` at the right boundary. The
post-materialization column search therefore penalizes connected output routes
whose selected port is not `machine-output`. This keeps the current default
sample on the less compact but runtime-proven 4x2 layout until the generator can
prove item flow from machine-output drop belts into learned edge buses.

Runtime validation now adds an output-unloading bottleneck audit. It inspects
recipe-machine output inventories, output inserters that pick up from those
machines, the inserters' held stacks, and the transport lines where those
inserters drop items. This closes the gap between the offline Machine I/O audit
and real throughput: the offline audit can say "there is an output inserter",
while the runtime marker can show whether that inserter actually keeps up. In
the current `iron-ore 2x turbo-transport-belt` recycle-merge sample, the runtime
marker reports five effective output inserters. After the output inserter
upgrade pass those effective inserters are `stack-inserter`, but the final
2400-tick probe still reports `machine_output_items=iron-ore:250` and four of
five crushers at `full_output`. That explains the low throughput-window result:
the current generated box is still output-unloading and lane-distribution
limited before it is right-boundary-belt limited.

The materialization report also includes a machine-output expansion audit and a
conservative materialization pass. The audit enumerates extra `stack-inserter`
positions around recipe machines, checks inserter and proposed drop-belt
collision boxes from data.raw, and rejects candidates that would drop below the
machine centerline or to the left of the machine in the current
left-input/right-output box. The materialization pass promotes the safest subset
first: extra inserters that can drop onto an existing same-tier belt. It does not
yet create independent new output lanes from scratch, because isolated drop
belts can bypass byproduct filtering or fail runtime placement unless they are
also routed and validated. In the current `iron-ore 2x turbo-transport-belt`
sample, this adds five extra `stack-inserter` unloaders, one per crusher.

The same sample also showed why route selection must prefer actual
`machine-output` drop lanes over ordinary edge buses. The old 4x2 candidate had
a structurally exact 2x turbo output contract, but one output route was an
edge-bus-style lane that did not carry enough runtime product. After preferring
machine-output lanes, the generator selects a taller 1x5 box with five
right-side machine-output lanes. This is over-provisioned relative to a strict
2-belt boundary, but the runtime throughput probe reaches post-startup windows
around `7188-7452/min` delivered `iron-ore` with a clean right boundary. The
next optimization target is therefore not "make product reach the boundary" but
"compress proven machine-output lanes back down to the requested boundary
contract without losing throughput or byproduct separation."

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
when both are structurally available. Full-belt root planning now overbuilds
complete root template instances per requested belt: for the current
`iron-ore` 2x turbo target, six copied `metallic-asteroid-crushing` cells are
planned because each cell contributes about `1575/min` and one turbo belt carries
`3600/min`.

Full-belt targets carry a boundary-contract audit. For a target such as `2x
turbo-transport-belt`, the audit expects exactly two connected output routes
using `turbo-transport-belt`. A 3x2 copied-crusher candidate can satisfy that
boundary contract offline, but its two output lanes each collect three machines:
the output lane load audit reports `4725/min > 3600/min` on both lanes, and a
2400-tick Factorio probe measured `0/min` delivered to the right boundary. The
layout selector therefore treats overloaded output lanes as a stronger rejection
than an over-provisioned boundary contract.

The current default `iron-ore` 2x turbo sample selects a 2x3 copied-crusher grid
with three right-side machine-output lanes. It is explicitly
`over-provisioned` relative to the requested `2x turbo-transport-belt` boundary,
but all three output lane load checks are `sufficient`: two lanes carry two
instances each at `3150/min <= 3600/min`, and the last carries one instance at
`1575/min`. The materializer now includes the source machine-output port in each
output fan-in path and may orient that plain transport belt east, so the route no
longer starts one tile after a vertical drop belt that Factorio would never
side-load into the generated boundary path.

The same sample still detects that `metallic-asteroid-crushing` can return
`metallic-asteroid-chunk` as a 0.2 probability item byproduct. The materializer
inserts three target-item filter splitters, keeps `iron-ore` on the main output
routes, and routes the recyclable chunk side outputs back to the left input
boundary with U-shaped recycle-return belts. This remains a generated diagnostic
geometry, not a proof that the recycle loop is fully drained or long-run stable.

The learned blueprint corpus also shows that inserter filters are common in
large black-box builds: inserters use `filters`, `use_filters`, and sometimes
`filter_mode` to keep mixed belts semantically clean. Blueprint Lab applies that
lesson to generated output expansion inserters. Extra output inserters are now
filtered to the target product, and the runtime validator restores those filters
in its direct-placement fallback with `LuaEntity::set_filter`.

Runtime probes against the 2x3 source-fan-in blueprint showed that a compact
output merge can silently break inserters. The runtime validator now reports
`invalid_output_inserters` when an inserter drops to a belt near a recipe
machine but Factorio assigns its `pickup_target` to something other than that
machine. One failed 2400-tick probe reported three such invalid inserters: the
output fan-in belt had crossed existing machine-output pickup positions, so
those inserters picked up from the belt instead of the crusher. The materializer
now treats machine-output pickup positions as blocked for output fan-in routes
and detours before the first protected pickup point. A fresh 2400-tick probe of
the current 2x3 sample imports 786 entities through the direct-placement
fallback, restores twenty-one inserter filters, reports
`invalid_output_inserters=0`, sees twenty-three effective machine-to-belt output
inserters, and records post-startup throughput windows around `8100/min` to
`9192/min`. The summary is `7539/min`, above the `2x turbo = 7200/min` test-sink
target, with no input items in the right-boundary throughput windows.

A first routed-new-drop-lane experiment is intentionally not enabled by
default. It generated 795 placeable entities, three new drop belts, and eighteen
filtered output expansion inserters, but the 2400-tick runtime audit still saw
only fifteen effective machine-to-belt output inserters and throughput did not
improve beyond the existing-drop-belt result. This means the offline endpoint
test is still too loose for new drop lanes: a pickup point can touch a
production machine's box without Factorio assigning that inserter a valid
`pickup_target`. Until `machine_output_expansion_candidates()` is aligned with
runtime pickup-target semantics, `materialize_machine_output_expansions()` keeps
`allow_new_drop_belts=False`.

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
Earlier probes are still useful as regression markers. The generated output has
moved from `0/min` on a broken exact 3x2 candidate, to about `4.0-4.5k/min`
after source-port fan-in, to about `5.3k/min` after filtered multi-inserter
unloading on existing drop belts, and then to a `7539/min` 2400-tick summary
after output fan-in routes learned to avoid machine-output pickup positions.
The current default passing sample then moved its byproduct filter splitters
closer to the selected machine-output ports by choosing the first removable
generated east belt instead of a fixed downstream offset. On the same
`iron-ore 2x turbo-transport-belt` target this reduced the generated sample
from 786 to 753 entities while keeping the runtime probe clean:
`manual_entities=753`, `manual_failures=0`, `invalid_output_inserters=0`, and
right-boundary throughput windows of `8172/9204/8952/8532/8448/8520/min`.
The 2400-tick summary was `7542/min`, still above the `7200/min` test-sink
target.

The requested external contract is still not solved. A forced exact 3x2
candidate now has exactly two right-side `turbo-transport-belt` output routes,
places 780 entities with no manual failures, restores 22 target-filtered output
expansion inserters, and reports `invalid_output_inserters=0`, but its best
300-tick throughput window was `7164/min`. Moving the byproduct filter splitter
nearer to the machine-output port reduced byproduct pollution on output drop
lines, but the best exact 3x2 follow-up still reached only `7152/min`. A 4x2
overbuild experiment also stayed below target at `7152/min`. The next
optimization target is therefore not general machine count, but a stricter
two-belt compression strategy that can fully saturate both final turbo belts
without letting byproducts consume output-lane slots.

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
