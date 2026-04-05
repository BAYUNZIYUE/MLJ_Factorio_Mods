local Public = {}
local platform_cache = require("scripts/platform_cache")

local function build_filters_signature(filters)
    local signature_parts = {}
    if filters == nil then
        return ""
    end
    for _, filter in pairs(filters) do
        if filter.value and filter.min then
            local quality = filter.value.quality or "normal"
            local import_from = ""
            if filter.import_from then
                import_from = filter.import_from.name or filter.import_from
            end
            signature_parts[#signature_parts + 1] = filter.value.name .. "(" .. quality .. ")=" .. tostring(filter.min) .. "@" .. import_from
        end
    end
    table.sort(signature_parts)
    return table.concat(signature_parts, ";")
end

local function ensure_state()
    storage.usqs = storage.usqs or {}
    storage.usqs.logistic_state = storage.usqs.logistic_state or {}
    return storage.usqs.logistic_state
end

function Public.on_init()
    ensure_state()
end

local function clear_auto_section(platform)
    if not (platform and platform.valid and platform.hub and platform.hub.valid) then
        return
    end
    local logistic_sections = platform.hub.get_logistic_sections()
    local section_usqs_name = "[Auto]UPS Saving Quality Ships-" .. tostring(platform.index)
    for _, section in pairs(logistic_sections.sections) do
        if section.valid and section.group == section_usqs_name then
            section.active = false
            section.filters = {}
            section.multiplier = 1
            break
        end
    end
end

local function is_logistic_platform(platform)
    return platform
            and platform.valid
            and platform.surface
            and platform.surface.valid
            and platform.hub
            and platform.hub.valid
            and platform.hub.quality.level > 0
            and platform.space_location ~= nil
end

function Public.reconcile_platforms(platforms)
    local logistic_state = ensure_state()
    local seen = {}
    for _, platform in pairs(platforms) do
        if platform and platform.valid then
            seen[platform.index] = true
            if not is_logistic_platform(platform) then
                clear_auto_section(platform)
                logistic_state[platform.index] = nil
            end
        end
    end

    for platform_index in pairs(logistic_state) do
        if not seen[platform_index] then
            logistic_state[platform_index] = nil
        end
    end
end

function Public.on_60th_tick_check_logistic_sections(platforms)
    local logistic_state = ensure_state()
    for _, platform in pairs(platforms) do
        if is_logistic_platform(platform) then
            examine_platform(platform)
        else
            clear_auto_section(platform)
            logistic_state[platform.index] = nil
        end
    end
end

function examine_platform(platform)
    local logistic_state = ensure_state()
    local hub = platform.hub
    local multiplier = 1 + math.ceil(hub.quality.level * 0.79)
    local logistic_sections = platform.hub.get_logistic_sections()
    local section_usqs = nil
    local section_usqs_name = "[Auto]UPS Saving Quality Ships-" .. tostring(platform.index)
    local total_need = {}
    for _, section in pairs(logistic_sections.sections) do
        if not section.valid then
            goto continue
        end
        if section.group == section_usqs_name then
            section_usqs = section
            goto continue
        end
        if not section.active then
            goto continue
        end
            local is_rmmc_section = section.type == defines.logistic_section_type.request_missing_materials_controlled
            for _, filter in pairs(section.filters) do
                if filter.value and filter.min and
                        (is_rmmc_section or (filter.import_from and filter.import_from.name == platform.space_location.name)) then
                    add_count(total_need, {
                        value = filter.value,
                        min = filter.min * section.multiplier,
                    })
                end
            end
        :: continue ::
    end

    if section_usqs == nil then
        section_usqs = logistic_sections.add_section(section_usqs_name)
    end

    local hub_inventory = hub.get_inventory(defines.inventory.hub_main)
    local ordered_keys = {}
    for key in pairs(total_need) do
        ordered_keys[#ordered_keys + 1] = key
    end
    table.sort(ordered_keys)

    local section_usqs_filters = {}
    for _, key in ipairs(ordered_keys) do
        local need = total_need[key]
        local exists_count = hub_inventory.get_item_count({ name = need.value.name, quality = need.value.quality })
        local count2 = (need.min - exists_count) * (multiplier - 1)
        if count2 > 0 then
            local filter_to_be_added = {
                value = need.value,
                min = count2,
                import_from = platform.space_location,
            }
            section_usqs_filters[#section_usqs_filters + 1] = filter_to_be_added
        end
    end

    local signature = build_filters_signature(section_usqs_filters)
    local platform_state = logistic_state[platform.index]
    local current_signature = build_filters_signature(section_usqs.filters)
    if platform_state ~= nil
            and platform_state.signature == signature
            and current_signature == signature
            and section_usqs.active
            and section_usqs.multiplier == 1 then
        return
    end

    section_usqs.active = true
    section_usqs.multiplier = 1
    section_usqs.filters = section_usqs_filters
    logistic_state[platform.index] = {
        signature = signature,
    }
    platform_cache.mark_logistic_active(platform)
end

function add_count(total_need, item_info)
    local quality = item_info.value.quality or "normal"
    local key = item_info.value.name .. "(" .. quality .. ")"
    if total_need[key] == nil then
        total_need[key] = {
            value = item_info.value,
            min = item_info.min,
        }
    else
        total_need[key].min = total_need[key].min + item_info.min
    end
end

return Public
