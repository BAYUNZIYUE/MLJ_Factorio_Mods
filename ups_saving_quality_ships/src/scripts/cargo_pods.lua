local Public = {}
local platform_cache = require("scripts/platform_cache")
local examine_cargo_pods

local function ensure_state()
    storage.usqs = storage.usqs or {}
    storage.usqs.processed_cargo_pods = storage.usqs.processed_cargo_pods or {}
    storage.usqs.tracked_cargo_pods = storage.usqs.tracked_cargo_pods or {}
    storage.usqs.tracked_cargo_pod_platforms = storage.usqs.tracked_cargo_pod_platforms or {}
    storage.usqs.tracked_cargo_pods_by_platform = storage.usqs.tracked_cargo_pods_by_platform or {}
    storage.usqs.inventory = storage.usqs.inventory or {}
    return storage.usqs
end

function Public.on_init()
    ensure_state()
end

local function build_item_full_name(name, quality)
    return name .. "(" .. tostring(quality) .. ")"
end

local function return_extra_to_hub_or_cache(hub_inventory, item, item_full_name, multiplier, extra_count)
    if extra_count <= 0 then
        return
    end

    local return_count = math.floor(extra_count / multiplier)
    local cache_count = extra_count - return_count * multiplier
    if return_count > 0 then
        local real_insert = hub_inventory.insert({ name = item.name, count = return_count, quality = item.quality })
        local failed_return = return_count - real_insert
        if failed_return > 0 then
            cache_count = cache_count + failed_return * multiplier
        end
    end
    if cache_count > 0 then
        insert(item_full_name, cache_count)
    end
end

local function clear_platform_bucket_if_empty(platform_index)
    local bucket = storage.usqs.tracked_cargo_pods_by_platform[platform_index]
    if bucket == nil then
        return
    end
    if next(bucket.cargo_pods) == nil then
        storage.usqs.tracked_cargo_pods_by_platform[platform_index] = nil
    end
end

local function clear_platform_bucket(platform_index, bucket)
    for unit_number in pairs(bucket.cargo_pods) do
        storage.usqs.tracked_cargo_pods[unit_number] = nil
        storage.usqs.tracked_cargo_pod_platforms[unit_number] = nil
    end
    storage.usqs.tracked_cargo_pods_by_platform[platform_index] = nil
end

local function mark_related_platform_active_by_surface(surface)
    if surface == nil or not surface.valid then
        return
    end
    local platform = platform_cache.get_platform_by_surface(surface.index)
    if platform ~= nil then
        platform_cache.mark_cargo_active(platform)
        platform_cache.mark_logistic_active(platform)
    end
end

local function mark_processed_cargo_pod(pod)
    if pod and pod.valid and pod.unit_number ~= nil then
        storage.usqs.processed_cargo_pods[pod.unit_number] = pod
    end
end

local function clear_processed_cargo_pod(unit_number)
    storage.usqs.processed_cargo_pods[unit_number] = nil
end

local function remove_tracked_cargo_pod_by_unit_number(unit_number)
    local platform_index = storage.usqs.tracked_cargo_pod_platforms[unit_number]
    storage.usqs.tracked_cargo_pods[unit_number] = nil
    storage.usqs.tracked_cargo_pod_platforms[unit_number] = nil
    if platform_index ~= nil then
        local bucket = storage.usqs.tracked_cargo_pods_by_platform[platform_index]
        if bucket ~= nil then
            bucket.cargo_pods[unit_number] = nil
            clear_platform_bucket_if_empty(platform_index)
        end
    end
end

local function set_tracked_cargo_pod(pod, platform)
    if pod == nil or not pod.valid or pod.unit_number == nil or platform == nil then
        return
    end
    local old_platform_index = storage.usqs.tracked_cargo_pod_platforms[pod.unit_number]
    if old_platform_index ~= nil and old_platform_index ~= platform.index then
        local old_bucket = storage.usqs.tracked_cargo_pods_by_platform[old_platform_index]
        if old_bucket ~= nil then
            old_bucket.cargo_pods[pod.unit_number] = nil
            clear_platform_bucket_if_empty(old_platform_index)
        end
    end

    storage.usqs.tracked_cargo_pods[pod.unit_number] = pod
    storage.usqs.tracked_cargo_pod_platforms[pod.unit_number] = platform.index
    local bucket = storage.usqs.tracked_cargo_pods_by_platform[platform.index]
    if bucket == nil then
        bucket = {
            platform = platform,
            cargo_pods = {},
        }
        storage.usqs.tracked_cargo_pods_by_platform[platform.index] = bucket
    else
        bucket.platform = platform
    end
    bucket.cargo_pods[pod.unit_number] = pod
end

local function collect_valid_bucket_pods(platform, bucket)
    local cargo_pods = {}
    local stale_pods = {}
    for unit_number, pod in pairs(bucket.cargo_pods) do
        if not (pod and pod.valid and pod.surface and pod.surface.valid) then
            stale_pods[#stale_pods + 1] = unit_number
        elseif pod.surface.index ~= platform.surface.index then
            stale_pods[#stale_pods + 1] = unit_number
        else
            cargo_pods[#cargo_pods + 1] = pod
        end
    end

    for _, unit_number in ipairs(stale_pods) do
        remove_tracked_cargo_pod_by_unit_number(unit_number)
    end

    return cargo_pods
end

local function handle_processed_pod_result(platform, pod, pod_inventory)
    if pod_inventory.is_empty() then
        clear_processed_cargo_pod(pod.unit_number)
        remove_tracked_cargo_pod_by_unit_number(pod.unit_number)
        pod.destroy()
        return
    end

    mark_processed_cargo_pod(pod)
    remove_tracked_cargo_pod_by_unit_number(pod.unit_number)
    mark_related_platform_active_by_surface(platform.surface)
end

local function is_valid_cargo_platform(platform)
    return platform
            and platform.valid
            and platform.surface
            and platform.surface.valid
            and platform.hub
            and platform.hub.valid
            and platform.hub.quality.level > 0
end

-- 每20tick检查一次所有飞船表面的所有货舱
function Public.on_20th_tick_check_cargo_pods()
    ensure_state()
    for platform_index, bucket in pairs(storage.usqs.tracked_cargo_pods_by_platform) do
        local platform = bucket.platform
        if not is_valid_cargo_platform(platform) then
            clear_platform_bucket(platform_index, bucket)
        else
            local cargo_pods = collect_valid_bucket_pods(platform, bucket)
            if #cargo_pods > 0 then
                bucket.platform = platform
                platform_cache.mark_cargo_active(platform)
                platform_cache.mark_logistic_active(platform)
                examine_cargo_pods(platform, cargo_pods)
            end
        end
    end
end

function Public.rebuild_tracked_cargo_pods(platforms)
    ensure_state()
    storage.usqs.tracked_cargo_pods = {}
    storage.usqs.tracked_cargo_pod_platforms = {}
    storage.usqs.tracked_cargo_pods_by_platform = {}
    for _, platform in pairs(platforms) do
        if is_valid_cargo_platform(platform) then
            local cargo_pods = platform.surface.find_entities_filtered({ type = "cargo-pod" })
            for _, pod in pairs(cargo_pods) do
                if pod.valid and pod.unit_number ~= nil then
                    set_tracked_cargo_pod(pod, platform)
                end
            end
        end
    end
end

function Public.track_cargo_pod(pod)
    ensure_state()
    if pod and pod.valid and pod.unit_number ~= nil then
        local platform = platform_cache.get_platform_by_surface(pod.surface.index)
        if platform ~= nil then
            set_tracked_cargo_pod(pod, platform)
            mark_related_platform_active_by_surface(pod.surface)
        end
    end
end

function Public.untrack_cargo_pod(pod)
    ensure_state()
    if pod and pod.unit_number ~= nil then
        if pod.surface and pod.surface.valid then
            mark_related_platform_active_by_surface(pod.surface)
        end
        clear_processed_cargo_pod(pod.unit_number)
        remove_tracked_cargo_pod_by_unit_number(pod.unit_number)
    end
end

examine_cargo_pods = function(platform, cargo_pods)
    local hub = platform.hub
    -- 倍率由太空平台枢纽的品质决定，hub.quality.level=0 1 2 3 5，multiplier=1 2 3 4 5
    local multiplier = 1 + math.ceil(hub.quality.level * 0.79)
    local hub_inventory = hub.get_inventory(defines.inventory.hub_main)
    for _, pod in pairs(cargo_pods) do
        if storage.usqs.processed_cargo_pods[pod.unit_number] ~= nil then
            goto continue
        end
        local pod_inventory = pod.get_inventory(defines.inventory.cargo_unit)
        -- 不处理承载玩家的货舱
        if pod_inventory.is_empty() then
            goto continue
        end
        -- 货舱来源为nil时，一定是地面到太空；否则，必定是火箭发射井、太空平台枢纽、扩展接驳站之一
        local from_ground = pod.cargo_pod_origin == nil or pod.cargo_pod_origin.type == "rocket-silo"
        if from_ground then
            -- 地面 -> 飞船
            -- 每种货物都移除x-1/x个（向上取整），多移除的物品放入全局缓存
            for _, item in pairs(pod_inventory.get_contents()) do
                local item_full_name = item.name .. "(" .. tostring(item.quality) .. ")"
                local total_count = item.count + remove(item_full_name)
                local pod_count = math.floor(total_count / multiplier)
                local count_diff = item.count - pod_count
                if count_diff > 0 then
                    pod_inventory.remove({ name = item.name, count = count_diff, quality = item.quality })
                elseif count_diff < 0 then
                    pod_inventory.insert({ name = item.name, count = -count_diff, quality = item.quality })
                end
                -- 将剩余的物品放回缓存
                local curr_count = pod_inventory.get_item_count({ name = item.name, quality = item.quality })
                insert(item_full_name, total_count - curr_count * multiplier)

                --game.print("↑pod" .. tostring(pod.unit_number) .. " " .. item_full_name .. " x " .. item.count .. " -> " .. curr_count)
            end
        else
            -- 飞船 -> 地面
            local contents = pod_inventory.get_contents()
            local target_surface = nil
            if pod.cargo_pod_destination.type == defines.cargo_destination.station then
                target_surface = pod.cargo_pod_destination.station.surface
            elseif pod.cargo_pod_destination.type == defines.cargo_destination.surface then
                target_surface = pod.cargo_pod_destination.surface
            else
                goto continue
            end
            -- 飞船停在星球上空还是已经飞走
            local spaceship_have_surface = platform.space_location ~= nil
                    and target_surface ~= nil
                    and platform.space_location.name == target_surface.name


            -- 新货舱发射到哪里
            local pod_destination = nil
            if pod.cargo_pod_destination.type == defines.cargo_destination.station then
                pod_destination = {
                    type = defines.cargo_destination.station,
                    station = pod.cargo_pod_destination.station,
                    hatch = nil,
                    transform_launch_products = pod.cargo_pod_destination.transform_launch_products,
                }
            else
                pod_destination = {
                    type = defines.cargo_destination.surface,
                    transform_launch_products = false,
                    surface = pod.cargo_pod_destination.surface,
                    position = nil,
                    land_at_exact_position = false,
                }
            end
            -- 向哪个货舱添加物品
            local curr_pod = nil
            local curr_pod_inventory = nil

            for _, item in pairs(contents) do
                -- 1:向原有货舱添加货物
                -- 2:向新货舱添加货物并投放
                -- 3:返还货物到飞船中心，无法返还的添加进mod背包
                local state
                if spaceship_have_surface then
                    if item.count >= prototypes.item[item.name].stack_size * 10 then
                        state = 3
                    else
                        state = 1
                    end
                else
                    state = 1
                end
                local item_full_name = build_item_full_name(item.name, item.quality)
                local cached_extra_count = remove(item_full_name)
                local simulated_extra_count = item.count * (multiplier - 1) + cached_extra_count
                local extra_delivery_count
                -- 飞船仍停在目标星球上空时，系统已经按当前真实需求完成下投，模组只负责返还模拟增量。
                if spaceship_have_surface then
                    extra_delivery_count = 0
                else
                    extra_delivery_count = simulated_extra_count
                end
                local left_count = extra_delivery_count
                local delivered_extra_count = 0
                local returned_extra_count = 0
                while left_count > 0 do
                    if state == 1 then
                        local real_insert = pod_inventory.insert({ name = item.name, count = left_count, quality = item.quality })
                        left_count = left_count - real_insert
                        delivered_extra_count = delivered_extra_count + real_insert

                        --local curr_count = pod_inventory.get_item_count({ name = item.name, quality = item.quality })
                        --game.print("↓pod" .. tostring(pod.unit_number) .. " " .. item_full_name .. " x " .. item.count .. " -> " .. curr_count .. "，仍需下投" .. left_count)

                        if left_count > 0 then
                            state = 2

                            if curr_pod == nil then
                                curr_pod = hub.create_cargo_pod()
                                if curr_pod == nil then
                                    --game.print("无法创建新的货舱")
                                    state = 3
                                else
                                    mark_processed_cargo_pod(curr_pod)
                                    curr_pod_inventory = curr_pod.get_inventory(defines.inventory.cargo_unit)
                                end
                            end
                        end
                    elseif state == 2 then
                        local real_insert = curr_pod_inventory.insert({ name = item.name, count = left_count, quality = item.quality })
                        left_count = left_count - real_insert
                        delivered_extra_count = delivered_extra_count + real_insert

                        --local curr_count = curr_pod_inventory.get_item_count({ name = item.name, quality = item.quality })
                        --game.print("↓pod" .. tostring(curr_pod.unit_number) .. " " .. item_full_name .. " x 0 -> " .. curr_count .. "，仍需下投" .. left_count)

                        if left_count > 0 then
                            curr_pod.cargo_pod_destination = pod_destination

                            curr_pod = hub.create_cargo_pod()
                            if curr_pod == nil then
                                --game.print("无法创建新的货舱")
                                state = 3
                            else
                                mark_processed_cargo_pod(curr_pod)
                                curr_pod_inventory = curr_pod.get_inventory(defines.inventory.cargo_unit)
                            end
                        end
                    elseif state == 3 then
                        return_extra_to_hub_or_cache(hub_inventory, item, item_full_name, multiplier, left_count)
                        returned_extra_count = returned_extra_count + left_count
                        left_count = 0
                    end
                end
                local skipped_extra_count = simulated_extra_count - extra_delivery_count
                local undelivered_extra_count = math.max(0, extra_delivery_count - delivered_extra_count - returned_extra_count)
                return_extra_to_hub_or_cache(
                        hub_inventory,
                        item,
                        item_full_name,
                        multiplier,
                        skipped_extra_count + undelivered_extra_count
                )
            end
            if curr_pod ~= nil then
                curr_pod.cargo_pod_destination = pod_destination
            end

        end
        handle_processed_pod_result(platform, pod, pod_inventory)
        :: continue ::
    end
end

function math.round(num)
    if num > 0 then
        return math.floor(num + 0.5)
    end
    return math.ceil(num - 0.5)
end

-- storage.usqs.inventory：<name(quality), count>
function insert(name, count)
    if storage.usqs.inventory[name] == nil then
        storage.usqs.inventory[name] = count
    else
        storage.usqs.inventory[name] = storage.usqs.inventory[name] + count
    end
end

function remove(name)
    if storage.usqs.inventory[name] == nil then
        return 0
    else
        local count = storage.usqs.inventory[name]
        storage.usqs.inventory[name] = nil
        return count
    end
end

-- 每300tick移除所有已交付的货舱
function Public.on_300th_tick_check_cargo_pods()
    ensure_state()
    local to_remove = {}
    for unit_number, pod in pairs(storage.usqs.processed_cargo_pods) do
        if not (pod and pod.valid) then
            table.insert(to_remove, unit_number)
        end
    end
    for _, unit_number in pairs(to_remove) do
        clear_processed_cargo_pod(unit_number)
        remove_tracked_cargo_pod_by_unit_number(unit_number)
    end
end

return Public
