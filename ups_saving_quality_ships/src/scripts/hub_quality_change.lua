local HUB_ENTITY_NAME = "space-platform-hub"
local MQS_ENTITY_CLONES_DATA_NAME = "entity-clones"

local function normalize_blueprint_quality(quality)
    if quality == nil then
        return "normal"
    end
    return quality
end

local function store_blueprint_quality(quality)
    if quality == "normal" then
        return nil
    end
    return quality
end

local function build_next_quality_map()
    local ordered = {}
    local next_quality = {}

    for _, quality in pairs(prototypes.quality) do
        ordered[#ordered + 1] = quality
        if quality.next then
            next_quality[quality.name] = quality.next.name
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
        next_quality[current] = next_quality[current] or ordered[index + 1].name
    end

    return next_quality
end

local function is_known_quality(quality)
    return quality ~= nil
            and quality ~= "quality-unknown"
            and prototypes.quality[quality] ~= nil
end

local function clone_quality_from_hub_entity_name(entity_name)
    if entity_name == HUB_ENTITY_NAME then
        return "normal"
    end
    if entity_name == nil then
        return nil
    end

    local suffix = "-" .. HUB_ENTITY_NAME
    if string.sub(entity_name, -#suffix) ~= suffix then
        return nil
    end

    local quality = string.sub(entity_name, 1, #entity_name - #suffix)
    if is_known_quality(quality) then
        return quality
    end
    return nil
end

local function add_hub_clone_name(quality_to_name, clone_name)
    local quality = clone_quality_from_hub_entity_name(clone_name)
    if quality ~= nil and quality ~= "normal" and prototypes.entity[clone_name] ~= nil then
        quality_to_name[quality] = clone_name
    end
end

local function add_mqs_mod_data_clones(quality_to_name)
    local mod_data = prototypes.mod_data and prototypes.mod_data[MQS_ENTITY_CLONES_DATA_NAME]
    if mod_data == nil or not mod_data.valid then
        return
    end

    local ok, clones = pcall(function()
        return mod_data.get(HUB_ENTITY_NAME)
    end)
    if not ok or type(clones) ~= "table" then
        ok, clones = pcall(function()
            return mod_data.data and mod_data.data[HUB_ENTITY_NAME]
        end)
    end
    if not ok or type(clones) ~= "table" then
        return
    end

    for _, clone_name in pairs(clones) do
        add_hub_clone_name(quality_to_name, clone_name)
    end
end

local function build_hub_clone_map()
    local quality_to_name = {
        normal = HUB_ENTITY_NAME,
    }

    add_mqs_mod_data_clones(quality_to_name)

    for quality in pairs(prototypes.quality) do
        if quality ~= "normal" and quality ~= "quality-unknown" then
            add_hub_clone_name(quality_to_name, quality .. "-" .. HUB_ENTITY_NAME)
        end
    end

    return quality_to_name
end

local function hub_entity_name_for_quality(quality)
    quality = normalize_blueprint_quality(quality)
    if quality == "normal" then
        return HUB_ENTITY_NAME
    end

    local quality_to_name = build_hub_clone_map()
    return quality_to_name[quality] or HUB_ENTITY_NAME
end

local function blueprint_hub_quality(bp_entity)
    local clone_quality = clone_quality_from_hub_entity_name(bp_entity.name)
    if clone_quality == nil then
        return nil
    end

    local stored_quality = normalize_blueprint_quality(bp_entity.quality)
    if is_known_quality(stored_quality) and stored_quality ~= "normal" then
        return stored_quality
    end
    return clone_quality
end

local function upgrade_hub_quality(bp_entity)
    local next_quality = build_next_quality_map()
    local current_quality = blueprint_hub_quality(bp_entity)
    if current_quality == nil then
        return false
    end
    local target_quality = next_quality[current_quality]
    if target_quality == nil then
        -- Boundary control: highest quality stays at highest quality.
        game.print({ "hub_quality_change.hub_quality_at_max", current_quality })
        return true
    end

    bp_entity.quality = store_blueprint_quality(target_quality)
    bp_entity.name = hub_entity_name_for_quality(target_quality)
    game.print({ "hub_quality_change.hub_quality_changed", current_quality, target_quality })
    return true
end

local function convert_bp(bp)
    local processed = false
    if bp and bp.is_blueprint_setup() then
        local blueprint_entities = bp.get_blueprint_entities() -- array[BlueprintEntity]?
        if blueprint_entities and #blueprint_entities > 0 then
            for _, bp_entity in pairs(blueprint_entities) do
                -- BlueprintEntity :: table
                if blueprint_hub_quality(bp_entity) ~= nil then
                    -- 修改hub品质，普通品质在蓝图内通常为nil。
                    local quality_changed = upgrade_hub_quality(bp_entity)
                    -- 移除所有未命名（sec.group=nil）且为空（sec.filters=nil）的编组
                    local request_filters = bp_entity.request_filters
                    if request_filters and request_filters.sections then
                        local new_sections = {}
                        for _, sec in ipairs(request_filters.sections) do
                            if sec.group or sec.filters then
                                table.insert(new_sections, sec)
                            end
                        end
                        for i, sec in ipairs(new_sections) do
                            sec.index = i
                        end
                        request_filters.sections = new_sections
                    end
                    processed = processed or quality_changed
                end
            end
            bp.set_blueprint_entities(blueprint_entities)
        end
    end
    return processed
end

local function convert_bps_item_stack(bps)
    local processed = false
    if bps and bps.valid_for_read then
        -- inventory: LuaInventory?
        local inventory = bps.get_inventory(defines.inventory.item_main)
        if inventory then
            for i = 1, #inventory do
                local bp = inventory[i]
                if bp and bp.valid_for_read and bp.is_blueprint then
                    if convert_bp(bp) then
                        processed = true
                    end
                elseif bp and bp.valid_for_read and bp.is_blueprint_book then
                    if convert_bps_item_stack(bp) then
                        processed = true
                    end
                end
            end
        end
    end
    return processed
end

local function convert_bps_record(bps)
    local processed = false
    if bps and bps.valid_for_write then
        -- contents: Read dictionary[ItemStackIndex -> LuaRecord]
        for _, bp in pairs(bps.contents) do
            if bp and bp.valid_for_write and bp.type == "blueprint" then
                if convert_bp(bp) then
                    processed = true
                end
            elseif bp and bp.valid_for_write and bp.type == "blueprint-book" then
                if convert_bps_record(bp) then
                    processed = true
                end
            end
        end
    end
    return processed
end

script.on_event(defines.events.on_lua_shortcut, function(event)
    local player = game.players[event.player_index]
    if event.prototype_name == "change-hub-quality" then
        local is_bp = false
        local processed = false
        -- 在背包里面的就是LuaItemStack
        local cursor_stack = player.cursor_stack -- LuaItemStack?
        -- LuaItemStack.valid_for_read 文档说明：
        -- Differs from the usual 'valid' in that 'valid' will be 'true' even if the item stack is blank but the entity
        -- that holds it is still valid.
        -- cursor_stack似乎不会为nil，要特别注意
        if cursor_stack then
            if cursor_stack.is_blueprint then
                is_bp = true
                if cursor_stack.valid_for_read and convert_bp(cursor_stack) then
                    processed = true
                end
            elseif cursor_stack.is_blueprint_book then
                is_bp = true
                if cursor_stack.valid_for_read and convert_bps_item_stack(cursor_stack) then
                    processed = true
                end
            end
        end
        -- 在蓝图库（个人蓝图/公共蓝图）里面的就是LuaRecord
        local cursor_record = player.cursor_record -- LuaRecord?
        -- LuaRecord.valid_for_write 文档说明：
        -- A record is invalid for write if it is a BlueprintRecord preview or if it is in the "My blueprints" shelf.
        if cursor_record then
            if cursor_record.type == "blueprint" then
                is_bp = true
                if cursor_record.valid_for_write and convert_bp(cursor_record) then
                    processed = true
                end
            elseif cursor_record.type == "blueprint-book" then
                is_bp = true
                if cursor_record.valid_for_write and convert_bps_record(cursor_record) then
                    processed = true
                end
            end
        end
        if not is_bp then
            player.print({ "hub_quality_change.tip_handing_blueprint" })
        elseif not processed then
            player.print({ "hub_quality_change.tip_invalid_for_read_write" })
        end
    end
end)
