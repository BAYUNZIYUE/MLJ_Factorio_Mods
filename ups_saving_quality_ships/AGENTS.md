# UPS Saving Quality Ships Notes

## OVERVIEW
Mixed data/runtime mod centered on platform quality, cargo pod handling, and logistics section rewriting for Space Age platforms.

## WHERE TO LOOK
- Metadata and dependency surface: `ups_saving_quality_ships/src/info.json`
- Runtime entry: `ups_saving_quality_ships/src/control.lua`
- Data stage: `ups_saving_quality_ships/src/data.lua`, `ups_saving_quality_ships/src/data-updates.lua`
- Runtime modules: `ups_saving_quality_ships/src/scripts/`
- User-facing rationale: `ups_saving_quality_ships/README.md`

## CONVENTIONS
- Runtime state is coordinated through `storage.usqs` and helper modules under `src/scripts/`.
- `control.lua` owns the event cadence; helper modules should stay reusable and avoid registering their own unrelated events.
- This mod depends on `space-age`; changes should assume Space Platform and cargo APIs are relevant.
- Quality-sensitive logic is central to behavior; preserve the multiplier assumptions described in the README unless you intend a design change.

## ANTI-PATTERNS
- Do not break the linkage between cargo tracking, platform cache rebuilds, and logistics-section reconciliation.
- Do not put prototype/data-stage edits into `src/scripts/`; that directory is runtime-only.

## NOTES
- `src/scripts/` has its own AGENTS because it is the real runtime domain boundary.
