local Public = {}
local platform_cache = require("scripts/platform_cache")
local quality_multiplier = require("scripts/quality_multiplier")

local AUTO_SECTION_PREFIXES = {
    en = "[Auto]UPS Saving Quality Ships-",
    zh = "[自动]UPS友好型品质飞船-",
}

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
    storage.usqs.logistic_locale = storage.usqs.logistic_locale or "en"
    return storage.usqs.logistic_state
end

local function normalize_locale(locale)
    if locale ~= nil and string.sub(locale, 1, 2) == "zh" then
        return "zh"
    end
    return "en"
end

local function build_auto_section_name(platform_index)
    local locale_key = storage.usqs.logistic_locale or "en"
    return AUTO_SECTION_PREFIXES[locale_key] .. tostring(platform_index)
end

local function is_auto_section_name(group_name, platform_index)
    if group_name == nil then
        return false
    end
    for _, prefix in pairs(AUTO_SECTION_PREFIXES) do
        if group_name == prefix .. tostring(platform_index) then
            return true
        end
    end
    return false
end

local function collect_auto_sections(logistic_sections, platform_index)
    local auto_sections = {}
    for _, section in pairs(logistic_sections.sections) do
        if section.valid and is_auto_section_name(section.group, platform_index) then
            auto_sections[#auto_sections + 1] = section
        end
    end
    table.sort(auto_sections, function(left, right)
        return left.index < right.index
    end)
    return auto_sections
end

local function remove_sections_by_index(logistic_sections, section_indexes)
    table.sort(section_indexes, function(left, right)
        return left > right
    end)
    for _, section_index in ipairs(section_indexes) do
        logistic_sections.remove_section(section_index)
    end
end

local function remove_auto_section(platform)
    if not (platform and platform.valid and platform.hub and platform.hub.valid) then
        return
    end
    local logistic_sections = platform.hub.get_logistic_sections()
    local auto_sections = collect_auto_sections(logistic_sections, platform.index)
    if #auto_sections == 0 then
        return
    end

    local section_indexes = {}
    for _, section in ipairs(auto_sections) do
        if section.is_manual then
            section_indexes[#section_indexes + 1] = section.index
        end
    end
    if #section_indexes > 0 then
        remove_sections_by_index(logistic_sections, section_indexes)
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

function Public.on_init()
    ensure_state()
    if game == nil or game.players == nil then
        return
    end
    for _, player in pairs(game.players) do
        if player and player.valid then
            Public.set_locale(player.locale)
            break
        end
    end
end

function Public.set_locale(locale)
    ensure_state()
    local normalized_locale = normalize_locale(locale)
    if storage.usqs.logistic_locale == normalized_locale then
        return false
    end
    storage.usqs.logistic_locale = normalized_locale
    storage.usqs.logistic_state = {}
    return true
end

function Public.reconcile_platforms(platforms)
    local logistic_state = ensure_state()
    local seen = {}
    for _, platform in pairs(platforms) do
        if platform and platform.valid then
            seen[platform.index] = true
            if not is_logistic_platform(platform) then
                remove_auto_section(platform)
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
            remove_auto_section(platform)
            logistic_state[platform.index] = nil
        end
    end
end

function examine_platform(platform)
    local logistic_state = ensure_state()
    local hub = platform.hub
    local multiplier = quality_multiplier.from_quality(hub.quality)
    local logistic_sections = platform.hub.get_logistic_sections()
    local section_usqs_name = build_auto_section_name(platform.index)
    local auto_sections = collect_auto_sections(logistic_sections, platform.index)
    local section_usqs = nil
    local duplicate_section_indexes = {}
    for _, section in ipairs(auto_sections) do
        if section_usqs == nil or section.group == section_usqs_name then
            if section_usqs ~= nil then
                duplicate_section_indexes[#duplicate_section_indexes + 1] = section_usqs.index
            end
            section_usqs = section
        else
            duplicate_section_indexes[#duplicate_section_indexes + 1] = section.index
        end
    end
    if #duplicate_section_indexes > 0 then
        remove_sections_by_index(logistic_sections, duplicate_section_indexes)
    end

    local total_need = {}
    for _, section in pairs(logistic_sections.sections) do
        if not section.valid then
            goto continue
        end
        if is_auto_section_name(section.group, platform.index) then
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

    if #section_usqs_filters == 0 then
        remove_auto_section(platform)
        logistic_state[platform.index] = nil
        return
    end

    if section_usqs == nil or not section_usqs.valid then
        section_usqs = logistic_sections.add_section(section_usqs_name)
    elseif section_usqs.group ~= section_usqs_name then
        section_usqs.group = section_usqs_name
    end

    local signature = build_filters_signature(section_usqs_filters)
    local platform_state = logistic_state[platform.index]
    local current_signature = build_filters_signature(section_usqs.filters)
    if platform_state ~= nil
            and platform_state.signature == signature
            and current_signature == signature
            and section_usqs.active
            and section_usqs.multiplier == 1
            and section_usqs.group == section_usqs_name then
        return
    end

    section_usqs.active = true
    section_usqs.multiplier = 1
    section_usqs.group = section_usqs_name
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
