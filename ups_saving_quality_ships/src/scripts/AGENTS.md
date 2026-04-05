# Quality Ships Script Notes

## OVERVIEW
Runtime mechanism layer for UPS Saving Quality Ships. Each file owns a distinct subsystem and they coordinate through `storage.usqs` plus `platform_cache`.

## WHERE TO LOOK
- Cache/indexing: `ups_saving_quality_ships/src/scripts/platform_cache.lua`
- Cargo pod tracking and cleanup: `ups_saving_quality_ships/src/scripts/cargo_pods.lua`
- Logistics section reconciliation: `ups_saving_quality_ships/src/scripts/logistic_section_change.lua`
- Blueprint hub-quality tooling: `ups_saving_quality_ships/src/scripts/hub_quality_change.lua`

## CONVENTIONS
- Keep subsystem boundaries clear: cache, cargo, logistics, and blueprint mutation are separate on purpose.
- Reuse `platform_cache` APIs rather than duplicating platform lookup logic.
- Preserve the existing tick cadence expectations from `control.lua` (20 / 60 / 300) when adjusting workload distribution.
- Shared persistent state belongs under `storage.usqs`; do not fragment it into unrelated global roots.

## ANTI-PATTERNS
- Do not access stale entities without validity checks; this directory already assumes entities and surfaces can disappear.
- Do not bypass cache invalidation or active-marking helpers when updating cargo/logistics state.
