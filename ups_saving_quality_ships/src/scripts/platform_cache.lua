local Public = {}

local CARGO_SHARDS = 4
local LOGISTIC_SHARDS = 2
local FULL_REBUILD_INTERVAL = 6

local function ensure_state()
    storage.usqs = storage.usqs or {}
    storage.usqs.platform_cache = storage.usqs.platform_cache or {
        all = {},
        cargo = {},
        logistic = {},
        by_surface_index = {},
        active_cargo = {},
        active_logistic = {},
        cargo_cursor = 1,
        logistic_cursor = 1,
        dirty = false,
        rebuild_counter = 0,
        cargo_active_turn = true,
        logistic_active_turn = true,
    }
    return storage.usqs.platform_cache
end

local function is_valid_platform(platform)
    return platform
            and platform.valid
            and platform.surface
            and platform.surface.valid
            and platform.hub
            and platform.hub.valid
end

local function normalize_cursor(cache, key, count)
    if count <= 0 then
        cache[key] = 1
    elseif cache[key] == nil or cache[key] > count then
        cache[key] = 1
    end
end

local function get_batch(list, cursor_key, shards)
    local cache = ensure_state()
    local count = #list
    if count == 0 then
        cache[cursor_key] = 1
        return {}
    end

    normalize_cursor(cache, cursor_key, count)

    local batch_size = math.max(1, math.ceil(count / shards))
    local start_index = cache[cursor_key]
    local end_index = math.min(start_index + batch_size - 1, count)
    local batch = {}

    for i = start_index, end_index do
        batch[#batch + 1] = list[i]
    end

    cache[cursor_key] = end_index + 1
    if cache[cursor_key] > count then
        cache[cursor_key] = 1
    end

    return batch
end

local function pop_active_batch(active, limit)
    local batch = {}
    for platform_index, platform in pairs(active) do
        active[platform_index] = nil
        if is_valid_platform(platform) and platform.hub.quality.level > 0 then
            batch[#batch + 1] = platform
            if #batch >= limit then
                break
            end
        end
    end
    return batch
end

local function get_limit(list, shards)
    return math.max(1, math.ceil(math.max(#list, 1) / shards))
end

local function get_active_quota(cache, quota_key, limit)
    if limit <= 1 then
        local use_active = cache[quota_key]
        cache[quota_key] = not use_active
        if use_active then
            return 1
        end
        return 0
    end
    return math.max(1, math.floor(limit / 2))
end

function Public.on_init()
    ensure_state()
end

function Public.rebuild()
    local cache = ensure_state()
    local all = {}
    local cargo = {}
    local logistic = {}
    local by_surface_index = {}

    for _, force in pairs(game.forces) do
        for _, platform in pairs(force.platforms) do
            if is_valid_platform(platform) then
                all[#all + 1] = platform
                if platform.hub.quality.level > 0 then
                    cargo[#cargo + 1] = platform
                    by_surface_index[platform.surface.index] = platform
                    if platform.space_location ~= nil then
                        logistic[#logistic + 1] = platform
                    end
                end
            end
        end
    end

    cache.all = all
    cache.cargo = cargo
    cache.logistic = logistic
    cache.by_surface_index = by_surface_index
    normalize_cursor(cache, "cargo_cursor", #cargo)
    normalize_cursor(cache, "logistic_cursor", #logistic)
    cache.dirty = false
    cache.rebuild_counter = 0
end

function Public.get_all_platforms()
    local cache = ensure_state()
    if #cache.all == 0 then
        Public.rebuild()
    end
    return cache.all
end

function Public.request_rebuild()
    local cache = ensure_state()
    cache.dirty = true
end

function Public.get_platform_by_surface(surface_index)
    local cache = ensure_state()
    return cache.by_surface_index[surface_index]
end

function Public.get_all_cargo_platforms()
    local cache = ensure_state()
    if #cache.cargo == 0 then
        Public.rebuild()
    end
    return cache.cargo
end

function Public.mark_cargo_active(platform)
    local cache = ensure_state()
    if is_valid_platform(platform) and platform.hub.quality.level > 0 then
        cache.active_cargo[platform.index] = platform
    end
end

function Public.mark_logistic_active(platform)
    local cache = ensure_state()
    if is_valid_platform(platform) and platform.hub.quality.level > 0 and platform.space_location ~= nil then
        cache.active_logistic[platform.index] = platform
    end
end

function Public.needs_rebuild()
    local cache = ensure_state()
    cache.rebuild_counter = cache.rebuild_counter + 1
    return cache.dirty or cache.rebuild_counter >= FULL_REBUILD_INTERVAL
end

function Public.get_cargo_batch()
    local cache = ensure_state()
    if #cache.cargo == 0 then
        Public.rebuild()
    end
    local limit = get_limit(cache.cargo, CARGO_SHARDS)
    local active_quota = get_active_quota(cache, "cargo_active_turn", limit)
    local batch = pop_active_batch(cache.active_cargo, active_quota)
    local seen = {}
    for _, platform in ipairs(batch) do
        seen[platform.index] = true
    end
    if #batch >= limit then
        return batch
    end
    local fallback = get_batch(cache.cargo, "cargo_cursor", CARGO_SHARDS)
    for _, platform in ipairs(fallback) do
        if #batch >= limit then
            break
        end
        if not seen[platform.index] then
            batch[#batch + 1] = platform
        end
    end
    return batch
end

function Public.get_logistic_batch()
    local cache = ensure_state()
    if #cache.logistic == 0 then
        Public.rebuild()
    end
    local limit = get_limit(cache.logistic, LOGISTIC_SHARDS)
    local active_quota = get_active_quota(cache, "logistic_active_turn", limit)
    local batch = pop_active_batch(cache.active_logistic, active_quota)
    local seen = {}
    for _, platform in ipairs(batch) do
        seen[platform.index] = true
    end
    if #batch >= limit then
        return batch
    end
    local fallback = get_batch(cache.logistic, "logistic_cursor", LOGISTIC_SHARDS)
    for _, platform in ipairs(fallback) do
        if #batch >= limit then
            break
        end
        if not seen[platform.index] then
            batch[#batch + 1] = platform
        end
    end
    return batch
end

return Public
