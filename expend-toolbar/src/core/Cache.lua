---@class Cache
---@generic K, V
---@field private _memory table<K, V>
---@field private _supplier fun(key: K):V
Cache = Object:extendAs("Cache")

---@generic K, V
---@param supplier fun(key: K):V
function Cache.new(supplier)
    local this = Cache:super(Object.new())
    this._memory = {}
    this._supplier = supplier
    return this
end

---@public
---@generic K, V
---@param key K
---@return V value or nil
function Cache:get(key)
    local cachedValue = self._memory[key]
    if cachedValue ~= nil and cachedValue ~= false then
        return cachedValue
    elseif cachedValue == false then
        return nil
    else
        local freshValue = self._supplier(key)
        if freshValue == nil then
            self._memory[key] = false
            return nil
        else
            self._memory[key] = freshValue
            return freshValue
        end
    end
end
