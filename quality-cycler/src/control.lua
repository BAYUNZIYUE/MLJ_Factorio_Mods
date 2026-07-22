local prefix = "quality-cycler-"
local mapper_sides = { "to" }
local debug_enabled = false
local ignore_list_setting_name = prefix .. "ignore-list"

local function new_result()
    return {
        blueprint_entities = 0,
        blueprint_items = 0,
        upgrade_rules = 0,
    }
end

local function add_result(total, part)
    total.blueprint_entities = total.blueprint_entities + (part.blueprint_entities or 0)
    total.blueprint_items = total.blueprint_items + (part.blueprint_items or 0)
    total.upgrade_rules = total.upgrade_rules + (part.upgrade_rules or 0)
end

local function result_changed(result)
    return result.blueprint_entities > 0
            or result.blueprint_items > 0
            or result.upgrade_rules > 0
end

local function localize_text(player, zh_text, en_text)
    if player and player.locale and string.sub(player.locale, 1, 2) == "zh" then
        return zh_text
    end
    return en_text
end

local function debug_log(message)
    if debug_enabled then
        log("[Quality Cycler Debug] " .. message)
    end
end

local function safe_value(callback)
    local ok, value = pcall(callback)
    if ok then
        if value == nil then
            return "nil"
        end
        return tostring(value)
    end
    return "ERR:" .. tostring(value)
end

local function describe_object(label, object)
    if object == nil then
        debug_log(label .. ": nil")
        return
    end

    debug_log(label
            .. " valid=" .. safe_value(function() return object.valid end)
            .. " name=" .. safe_value(function() return object.name end)
            .. " type=" .. safe_value(function() return object.type end)
            .. " valid_for_read=" .. safe_value(function() return object.valid_for_read end)
            .. " valid_for_write=" .. safe_value(function() return object.valid_for_write end)
            .. " is_blueprint=" .. safe_value(function() return object.is_blueprint end)
            .. " is_blueprint_book=" .. safe_value(function() return object.is_blueprint_book end)
            .. " is_upgrade_item=" .. safe_value(function() return object.is_upgrade_item end)
            .. " mapper_count=" .. safe_value(function() return object.mapper_count end))
end

local function describe_gui_element(label, element)
    if element == nil then
        debug_log(label .. ": nil")
        return
    end

    debug_log(label
            .. " valid=" .. safe_value(function() return element.valid end)
            .. " name=" .. safe_value(function() return element.name end)
            .. " type=" .. safe_value(function() return element.type end)
            .. " caption=" .. safe_value(function() return serpent.line(element.caption) end)
            .. " tooltip=" .. safe_value(function() return serpent.line(element.tooltip) end)
            .. " elem_type=" .. safe_value(function() return element.elem_type end)
            .. " elem_value=" .. safe_value(function() return serpent.line(element.elem_value) end)
            .. " tags=" .. safe_value(function() return serpent.line(element.tags) end)
            .. " index=" .. safe_value(function() return element.get_index_in_parent() end))

    local parent = element.parent
    for depth = 1, 5 do
        if parent == nil then
            debug_log(label .. ".parent" .. tostring(depth) .. ": nil")
            return
        end
        debug_log(label .. ".parent" .. tostring(depth)
                .. " valid=" .. safe_value(function() return parent.valid end)
                .. " name=" .. safe_value(function() return parent.name end)
                .. " type=" .. safe_value(function() return parent.type end)
                .. " tags=" .. safe_value(function() return serpent.line(parent.tags) end)
                .. " index=" .. safe_value(function() return parent.get_index_in_parent() end))
        parent = parent.parent
    end
end

local function describe_selected_prototype(prototype)
    if prototype == nil then
        debug_log("selected_prototype: nil")
        return
    end

    debug_log("selected_prototype"
            .. " name=" .. safe_value(function() return prototype.name end)
            .. " type=" .. safe_value(function() return prototype.type end)
            .. " derived_type=" .. safe_value(function() return prototype.derived_type end)
            .. " base_type=" .. safe_value(function() return prototype.base_type end))
end

local function debug_event_context(event, player)
    debug_log("event input=" .. tostring(event.input_name)
            .. " player_index=" .. tostring(event.player_index)
            .. " opened_gui_type=" .. safe_value(function() return player.opened_gui_type end)
            .. " mod_gui_top_children=" .. safe_value(function() return #player.gui.top.children end)
            .. " screen_children=" .. safe_value(function() return #player.gui.screen.children end)
            .. " relative_children=" .. safe_value(function() return #player.gui.relative.children end)
            .. " cursor_empty=" .. safe_value(function() return player.is_cursor_empty() end))
    describe_selected_prototype(event.selected_prototype)
    describe_gui_element("event.element", event.element)
    describe_object("cursor_stack", player.cursor_stack)
    describe_object("cursor_record", player.cursor_record)
    describe_object("opened", player.opened)
    describe_object("opened_self", player.opened_self)
    describe_object("selected", player.selected)
end

local function build_quality_maps()
    local ordered = {}
    local next_quality = {}
    local previous_quality = {}

    for _, quality in pairs(prototypes.quality) do
        ordered[#ordered + 1] = quality
        if quality.next then
            next_quality[quality.name] = quality.next.name
            previous_quality[quality.next.name] = quality.name
        end
    end

    table.sort(ordered, function(left, right)
        local left_level = left.level or 0
        local right_level = right.level or 0
        if left_level ~= right_level then
            return left_level < right_level
        end
        return (left.order or left.name) < (right.order or right.name)
    end)

    for index = 1, #ordered - 1 do
        local current = ordered[index].name
        local next_name = ordered[index + 1].name
        next_quality[current] = next_quality[current] or next_name
        previous_quality[next_name] = previous_quality[next_name] or current
    end

    return next_quality, previous_quality, ordered
end

local function first_target_quality(next_quality, ordered)
    if next_quality["normal"] ~= nil then
        return next_quality["normal"]
    end

    if ordered[1] ~= nil then
        return ordered[1].name
    end
    return nil
end

local function build_ignored_names(player)
    local player_settings = settings.get_player_settings(player)
    local setting = player_settings and player_settings[ignore_list_setting_name]
    local raw_value = ""
    if setting ~= nil and setting.value ~= nil then
        raw_value = tostring(setting.value)
    end

    local ignored_names = {}
    -- 兼容中文逗号，方便直接从中文说明里复制配置。
    raw_value = string.gsub(raw_value, "，", ",")
    for name in string.gmatch(raw_value, "([^,]+)") do
        name = string.gsub(name, "^%s+", "")
        name = string.gsub(name, "%s+$", "")
        if name ~= "" then
            ignored_names[name] = true
        end
    end
    return ignored_names
end

local function is_ignored_name(ignored_names, name)
    return name ~= nil and ignored_names ~= nil and ignored_names[name] == true
end

local function values_differ(left, right)
    if type(left) ~= type(right) then
        return true
    end
    if type(left) == "number" then
        return math.abs(left - right) > 0.000001
    end
    if type(left) == "table" then
        return serpent.line(left) ~= serpent.line(right)
    end
    return left ~= right
end

local function method_value_changes_with_quality(prototype, method_name, target_quality)
    local method = prototype and prototype[method_name]
    if type(method) ~= "function" then
        return false
    end

    local normal_ok, normal_value = pcall(function()
        return method("normal")
    end)
    local target_ok, target_value = pcall(function()
        return method(target_quality)
    end)
    if not (normal_ok and target_ok) then
        return false
    end
    return values_differ(normal_value, target_value)
end

local function custom_tooltip_changes_with_quality(prototype)
    local fields = prototype and prototype.custom_tooltip_fields
    if type(fields) ~= "table" then
        return false
    end

    for _, field in pairs(fields) do
        local quality_values = field and field.quality_values
        if type(quality_values) == "table" and next(quality_values) ~= nil then
            return true
        end
    end
    return false
end

local excluded_entity_types = {
    ["transport-belt"] = true,
    ["underground-belt"] = true,
    ["splitter"] = true,
}

local included_entity_types = {
    ["ammo-turret"] = true,
    ["artillery-turret"] = true,
    ["asteroid-collector"] = true,
    ["cargo-bay"] = true,
    ["electric-turret"] = true,
    ["fluid-turret"] = true,
    ["fusion-generator"] = true,
    ["fusion-reactor"] = true,
    ["heating-tower"] = true,
    ["lab"] = true,
    ["lightning-attractor"] = true,
    ["logistic-container"] = true,
    ["pump"] = true,
    ["reactor"] = true,
    ["roboport"] = true,
    ["thruster"] = true,
}

local function inventory_size_changes_with_quality(entity_prototype, target_quality)
    if entity_prototype == nil or type(entity_prototype.get_inventory_size) ~= "function" then
        return false
    end

    for _, inventory_index in pairs(defines.inventory) do
        local normal_ok, normal_value = pcall(function()
            return entity_prototype.get_inventory_size(inventory_index, "normal")
        end)
        local target_ok, target_value = pcall(function()
            return entity_prototype.get_inventory_size(inventory_index, target_quality)
        end)
        if normal_ok and target_ok and values_differ(normal_value, target_value) then
            return true
        end
    end
    return false
end

local entity_quality_methods = {
    "get_crafting_speed",
    "get_supply_area_distance",
    "get_max_wire_distance",
    "get_max_circuit_wire_distance",
    "get_max_energy_usage",
    "get_max_energy_production",
    "get_max_energy",
    "get_inserter_extension_speed",
    "get_inserter_rotation_speed",
    "get_researching_speed",
    "get_max_distance_of_sector_revealed",
    "get_max_distance_of_nearby_sector_revealed",
    "get_fluid_usage_per_tick",
    "get_max_power_output",
    "get_pumping_speed",
    "get_valve_flow_rate",
    "get_mining_drill_radius",
    "get_fluid_capacity",
    "get_attraction_range_elongation",
    "get_energy_distribution_efficiency",
}

local function entity_quality_affects_properties(entity_prototype, target_quality)
    if entity_prototype == nil or target_quality == nil then
        return false
    end

    if excluded_entity_types[entity_prototype.type] then
        return false
    end
    if included_entity_types[entity_prototype.type] then
        return true
    end
    if custom_tooltip_changes_with_quality(entity_prototype) then
        return true
    end
    if inventory_size_changes_with_quality(entity_prototype, target_quality) then
        return true
    end
    for _, method_name in ipairs(entity_quality_methods) do
        if method_value_changes_with_quality(entity_prototype, method_name, target_quality) then
            return true
        end
    end
    return false
end

local equipment_quality_methods = {
    "get_shield",
    "get_energy_consumption",
    "get_inventory_bonus",
    "get_movement_bonus",
}

local function equipment_quality_affects_properties(equipment_prototype, target_quality)
    if equipment_prototype == nil or target_quality == nil then
        return false
    end

    if custom_tooltip_changes_with_quality(equipment_prototype) then
        return true
    end
    for _, method_name in ipairs(equipment_quality_methods) do
        if method_value_changes_with_quality(equipment_prototype, method_name, target_quality) then
            return true
        end
    end
    return false
end

local item_quality_methods = {
    "get_spoil_ticks",
    "get_inventory_size_bonus",
    "get_module_effects",
    "get_durability",
}

local function item_quality_affects_properties(item_prototype, target_quality)
    if item_prototype == nil or target_quality == nil then
        return false
    end

    if custom_tooltip_changes_with_quality(item_prototype) then
        return true
    end
    if item_prototype.place_result
            and entity_quality_affects_properties(item_prototype.place_result, target_quality) then
        return true
    end
    if item_prototype.place_as_equipment_result
            and equipment_quality_affects_properties(item_prototype.place_as_equipment_result, target_quality) then
        return true
    end
    for _, method_name in ipairs(item_quality_methods) do
        if method_value_changes_with_quality(item_prototype, method_name, target_quality) then
            return true
        end
    end
    return false
end

local function mapper_target_is_allowed(mapper, target_quality, ignored_names)
    if mapper == nil or mapper.name == nil or target_quality == nil then
        return true
    end
    if is_ignored_name(ignored_names, mapper.name) then
        return false
    end
    if mapper.type == "entity" then
        return entity_quality_affects_properties(prototypes.entity[mapper.name], target_quality)
    end
    if mapper.type == "item" then
        return item_quality_affects_properties(prototypes.item[mapper.name], target_quality)
    end
    return true
end

local function normalize_stored_quality(quality)
    if quality == "normal" then
        return nil
    end
    return quality
end

local function quality_for_affect_check(current_quality, shifted_quality)
    if shifted_quality == "normal" and current_quality ~= nil then
        return current_quality
    end
    return shifted_quality
end

local function shift_quality(quality, increase, next_quality, previous_quality, ordered, keep_any)
    if quality == nil then
        if increase then
            local first_quality = first_target_quality(next_quality, ordered)
            return first_quality, first_quality ~= nil
        end
        return nil, false
    end
    if keep_any and quality == "any" then
        return quality, false
    end

    local shifted = nil
    if increase then
        shifted = next_quality[quality]
    else
        shifted = previous_quality[quality]
    end
    if shifted == nil then
        return quality, false
    end
    return shifted, shifted ~= quality
end

local function shift_named_entity_quality(entity_name, quality, increase, next_quality, previous_quality, ordered, ignored_names)
    if is_ignored_name(ignored_names, entity_name) then
        debug_log("skip ignored blueprint entity name=" .. tostring(entity_name))
        return quality, false
    end

    local shifted, did_change = shift_quality(quality, increase, next_quality, previous_quality, ordered, false)
    if not did_change then
        return quality, false
    end
    local affect_quality = quality_for_affect_check(quality, shifted)
    if not entity_quality_affects_properties(prototypes.entity[entity_name], affect_quality) then
        debug_log("skip quality-stable blueprint entity name=" .. tostring(entity_name)
                .. " target_quality=" .. tostring(shifted))
        return quality, false
    end
    return normalize_stored_quality(shifted), true
end

local function shift_named_item_quality(item_name, quality, increase, next_quality, previous_quality, ordered, ignored_names)
    if is_ignored_name(ignored_names, item_name) then
        debug_log("skip ignored blueprint item name=" .. tostring(item_name))
        return quality, false
    end

    local shifted, did_change = shift_quality(quality, increase, next_quality, previous_quality, ordered, false)
    if not did_change then
        return quality, false
    end
    local affect_quality = quality_for_affect_check(quality, shifted)
    if not item_quality_affects_properties(prototypes.item[item_name], affect_quality) then
        debug_log("skip quality-stable blueprint item name=" .. tostring(item_name)
                .. " target_quality=" .. tostring(shifted))
        return quality, false
    end
    return normalize_stored_quality(shifted), true
end

local function shift_mapper_quality(mapper, increase, next_quality, previous_quality, ordered, ignored_names)
    if mapper == nil then
        return nil, false
    end

    local shifted, did_change = shift_quality(mapper.quality, increase, next_quality, previous_quality, ordered, false)
    local affect_quality = quality_for_affect_check(mapper.quality, shifted)
    if did_change and not mapper_target_is_allowed(mapper, affect_quality, ignored_names) then
        debug_log("skip ignored mapper type=" .. tostring(mapper.type)
                .. " name=" .. tostring(mapper.name)
                .. " target_quality=" .. tostring(shifted))
        return mapper, false
    end

    mapper.quality = normalize_stored_quality(shifted)
    return mapper, did_change
end

local function update_blueprint(blueprint, increase, ignored_names)
    if not blueprint.is_blueprint_setup() then
        return new_result(), true
    end

    local entities = blueprint.get_blueprint_entities()
    if entities == nil then
        return new_result(), true
    end

    local next_quality, previous_quality, ordered = build_quality_maps()
    local result = new_result()

    for _, entity in pairs(entities) do
        local entity_quality, entity_changed = shift_named_entity_quality(
                entity.name,
                entity.quality,
                increase,
                next_quality,
                previous_quality,
                ordered,
                ignored_names
        )
        if entity_changed then
            entity.quality = entity_quality
            result.blueprint_entities = result.blueprint_entities + 1
        end

        if entity.items then
            for _, insert_plan in pairs(entity.items) do
                if insert_plan.id and insert_plan.id.name then
                    local item_quality, item_changed = shift_named_item_quality(
                            insert_plan.id.name,
                            insert_plan.id.quality,
                            increase,
                            next_quality,
                            previous_quality,
                            ordered,
                            ignored_names
                    )
                    if item_changed then
                        insert_plan.id.quality = item_quality
                        result.blueprint_items = result.blueprint_items + 1
                    end
                end
            end
        end
    end

    if not result_changed(result) then
        return result, true
    end

    local ok, err = pcall(function()
        blueprint.set_blueprint_entities(entities)
    end)
    if not ok then
        debug_log("set_blueprint_entities failed err=" .. tostring(err))
        return result, false
    end

    return result, true
end

local function update_upgrade_planner(upgrade_planner, increase, ignored_names)
    local next_quality, previous_quality, ordered = build_quality_maps()
    local result = new_result()
    local mapper_count = upgrade_planner.mapper_count or 0

    for index = 1, mapper_count do
        for _, mapper_side in ipairs(mapper_sides) do
            local mapper = upgrade_planner.get_mapper(index, mapper_side)
            local shifted_mapper, did_change = shift_mapper_quality(
                    mapper,
                    increase,
                    next_quality,
                    previous_quality,
                    ordered,
                    ignored_names
            )
            if did_change then
                local ok, err = pcall(function()
                    upgrade_planner.set_mapper(index, mapper_side, shifted_mapper)
                end)
                if ok then
                    result.upgrade_rules = result.upgrade_rules + 1
                else
                    debug_log("set_mapper failed index=" .. tostring(index)
                            .. " side=" .. tostring(mapper_side)
                            .. " err=" .. tostring(err))
                    return result, false
                end
            end
        end
    end

    return result, true
end

local function get_upgrade_planner_candidate(player)
    local cursor_stack = player.cursor_stack
    if cursor_stack and cursor_stack.valid and cursor_stack.valid_for_read and cursor_stack.is_upgrade_item then
        return cursor_stack, "cursor_stack", true
    end

    local cursor_record = player.cursor_record
    if cursor_record and cursor_record.type == "upgrade-planner" then
        return cursor_record, "cursor_record", cursor_record.valid_for_write
    end

    return nil, nil, false
end

local function get_blueprint_candidate(player)
    local cursor_stack = player.cursor_stack
    if cursor_stack and cursor_stack.valid and cursor_stack.valid_for_read and cursor_stack.is_blueprint then
        return cursor_stack, "cursor_stack", true
    end

    local cursor_record = player.cursor_record
    if cursor_record and cursor_record.type == "blueprint" then
        return cursor_record, "cursor_record", cursor_record.valid_for_write
    end

    return nil, nil, false
end

local function update_item_stack_or_record(item, increase, ignored_names)
    if item == nil then
        return new_result(), true, false
    end

    if safe_value(function() return item.is_upgrade_item end) == "true"
            or safe_value(function() return item.type end) == "upgrade-planner" then
        local result, writable = update_upgrade_planner(item, increase, ignored_names)
        return result, writable, true
    end

    if safe_value(function() return item.is_blueprint end) == "true"
            or safe_value(function() return item.type end) == "blueprint" then
        local result, writable = update_blueprint(item, increase, ignored_names)
        return result, writable, true
    end

    if safe_value(function() return item.is_blueprint_book end) == "true"
            or safe_value(function() return item.type end) == "blueprint-book" then
        local result, writable = update_blueprint_book(item, increase, ignored_names)
        return result, writable, true
    end

    return new_result(), true, false
end

function update_blueprint_book(book, increase, ignored_names)
    local total = new_result()
    local inventory = nil
    local ok_inventory, inventory_value = pcall(function()
        return book.get_inventory(defines.inventory.item_main)
    end)
    if ok_inventory then
        inventory = inventory_value
    end

    if inventory ~= nil then
        for index = 1, #inventory do
            local stack = inventory[index]
            if stack and stack.valid_for_read then
                local result, writable = update_item_stack_or_record(stack, increase, ignored_names)
                if not writable then
                    return total, false
                end
                add_result(total, result)
            end
        end
        return total, true
    end

    local contents = nil
    local ok_contents, contents_value = pcall(function()
        return book.contents
    end)
    if ok_contents then
        contents = contents_value
    end

    if contents ~= nil then
        for _, record in pairs(contents) do
            local result, writable = update_item_stack_or_record(record, increase, ignored_names)
            if not writable then
                return total, false
            end
            add_result(total, result)
        end
    end
    return total, true
end

local function get_blueprint_book_candidate(player)
    local cursor_stack = player.cursor_stack
    if cursor_stack and cursor_stack.valid and cursor_stack.valid_for_read and cursor_stack.is_blueprint_book then
        return cursor_stack, "cursor_stack", true
    end

    local cursor_record = player.cursor_record
    if cursor_record and cursor_record.type == "blueprint-book" then
        return cursor_record, "cursor_record", cursor_record.valid_for_write
    end

    return nil, nil, false
end

local function print_result(player, result)
    if not result_changed(result) then
        player.print({ "quality-cycler.no-quality-changed" })
        return
    end

    player.print(localize_text(
            player,
            "已更新 " .. tostring(result.blueprint_entities)
                    .. " 个蓝图建筑、" .. tostring(result.blueprint_items)
                    .. " 个蓝图物品、" .. tostring(result.upgrade_rules)
                    .. " 条升级规划器规则。",
            "Updated " .. tostring(result.blueprint_entities)
                    .. " blueprint building(s), " .. tostring(result.blueprint_items)
                    .. " blueprint item(s), and " .. tostring(result.upgrade_rules)
                    .. " upgrade-planner rule(s)."
    ))
end

local function on_quality_cycle(event)
    local player = game.get_player(event.player_index)
    if not (player and player.valid) then
        return
    end

    if debug_enabled then
        debug_event_context(event, player)
    end
    local ignored_names = build_ignored_names(player)

    local upgrade_planner, source, writable = get_upgrade_planner_candidate(player)
    if upgrade_planner ~= nil then
        debug_log("accepted upgrade planner source=" .. tostring(source)
                .. " writable=" .. tostring(writable)
                .. " mapper_count=" .. safe_value(function() return upgrade_planner.mapper_count end))
        if not writable then
            player.print({ "quality-cycler.read-only" })
            return
        end

        local result, writable_result = update_upgrade_planner(
                upgrade_planner,
                event.input_name == prefix .. "cycle-quality-up",
                ignored_names
        )
        debug_log("updated mapper qualities result=" .. serpent.line(result)
                .. " writable_result=" .. tostring(writable_result))
        if not writable_result then
            player.print({ "quality-cycler.read-only" })
            return
        end

        print_result(player, result)
        return
    end

    local blueprint, blueprint_source, blueprint_writable = get_blueprint_candidate(player)
    if blueprint ~= nil then
        debug_log("accepted blueprint source=" .. tostring(blueprint_source)
                .. " writable=" .. tostring(blueprint_writable)
                .. " entity_count=" .. safe_value(function() return blueprint.get_blueprint_entity_count() end))
        if not blueprint_writable then
            player.print({ "quality-cycler.read-only" })
            return
        end

        local result, writable_result = update_blueprint(
                blueprint,
                event.input_name == prefix .. "cycle-quality-up",
                ignored_names
        )
        debug_log("updated blueprint qualities result=" .. serpent.line(result)
                .. " writable_result=" .. tostring(writable_result))
        if not writable_result then
            player.print({ "quality-cycler.read-only" })
            return
        end

        print_result(player, result)
        return
    end

    local book, book_source, book_writable = get_blueprint_book_candidate(player)
    if book ~= nil then
        debug_log("accepted blueprint book source=" .. tostring(book_source)
                .. " writable=" .. tostring(book_writable))
        if not book_writable then
            player.print({ "quality-cycler.read-only" })
            return
        end

        local result, writable_result = update_blueprint_book(
                book,
                event.input_name == prefix .. "cycle-quality-up",
                ignored_names
        )
        debug_log("updated blueprint book qualities result=" .. serpent.line(result)
                .. " writable_result=" .. tostring(writable_result))
        if not writable_result then
            player.print({ "quality-cycler.read-only" })
            return
        end

        print_result(player, result)
        return
    end

    return
end

script.on_event(prefix .. "cycle-quality-up", on_quality_cycle)
script.on_event(prefix .. "cycle-quality-down", on_quality_cycle)
