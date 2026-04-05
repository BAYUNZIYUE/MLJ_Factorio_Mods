local cargo_pods = require("scripts/cargo_pods")
local logistic_section_change = require("scripts/logistic_section_change")
local platform_cache = require("scripts/platform_cache")
require("scripts/hub_quality_change")

local function rebuild_runtime_state()
    cargo_pods.on_init()
    logistic_section_change.on_init()
    platform_cache.on_init()
    platform_cache.rebuild()
    logistic_section_change.reconcile_platforms(platform_cache.get_all_platforms())
    cargo_pods.rebuild_tracked_cargo_pods(platform_cache.get_all_cargo_platforms())
end

script.on_init(rebuild_runtime_state)
script.on_configuration_changed(rebuild_runtime_state)

local function request_platform_cache_rebuild()
    platform_cache.request_rebuild()
end

local function on_cargo_pod_finished_descending(event)
    cargo_pods.track_cargo_pod(event.cargo_pod)
end

local function on_cargo_pod_left_surface(event)
    cargo_pods.untrack_cargo_pod(event.cargo_pod)
end

script.on_event(defines.events.on_space_platform_changed_state, request_platform_cache_rebuild)
script.on_event(defines.events.on_space_platform_built_entity, request_platform_cache_rebuild)
script.on_event(defines.events.on_space_platform_mined_entity, request_platform_cache_rebuild)
script.on_event(defines.events.on_force_created, request_platform_cache_rebuild)
script.on_event(defines.events.on_forces_merged, request_platform_cache_rebuild)
script.on_event(defines.events.on_cargo_pod_finished_descending, on_cargo_pod_finished_descending)
script.on_event(defines.events.on_cargo_pod_started_ascending, on_cargo_pod_left_surface)
script.on_event(defines.events.on_cargo_pod_delivered_cargo, on_cargo_pod_left_surface)
script.on_event(defines.events.on_cargo_pod_finished_ascending, on_cargo_pod_left_surface)

script.on_nth_tick(20, function()
    cargo_pods.on_20th_tick_check_cargo_pods()
end)

script.on_nth_tick(60, function()
    logistic_section_change.on_60th_tick_check_logistic_sections(platform_cache.get_logistic_batch())
end)

script.on_nth_tick(300, function()
    cargo_pods.on_300th_tick_check_cargo_pods()
    if platform_cache.needs_rebuild() then
        platform_cache.rebuild()
        logistic_section_change.reconcile_platforms(platform_cache.get_all_platforms())
        cargo_pods.rebuild_tracked_cargo_pods(platform_cache.get_all_cargo_platforms())
    end
end)
