if false then
    require("lang.Object")
    require("lang.collections.List")
end

---@generic K, V
---@class Map : Object
---@field private _map table<K,V>
Map = Object:extendAs("lang.collections.Map")

---@public
---@generic K, V
---@param keyType K
---@param valueType V
---@param table table<K,V> optional
---@return Map<K,V>
function Map.new(keyType, valueType, table)
    local this = Map:super(Object.new())
    this._map = table and table or {}
    return this
end

---@generic T
---@param value T
function Map:set(key, value)
    self._map[key] = value
end

---@public
---@generic K, V
---@param self Map<K,V>
---@param key K
function Map:get(key) end

---@public
---@generic K,V
---@param self Map<K,V>
---@param key K
---@return V
function Map.get(self, key)
    return self._map[key]
end

---@public
---@generic K
---@param key K
---@return boolean
function Map:contains(key)
    return self._map[key] ~= nil
end

---@public
---@return boolean
function Map:isEmpty()
    return next(self._map) == nil
end

---@public
---@generic K, V
---@param self Map<K,V>
---@param consumer fun(key:K, value:V):void
function Map:forEach(consumer) end

---@public
---@generic K, V
---@param self Map<K,V>
---@param consumer fun(key:K, value:V):void
function Map.forEach(self, consumer)
    for key, value in pairs(self._map) do
        consumer(key, value)
    end
end

---@public
---@generic K, V
---@param self Map<K,V>
---@param filter fun(key:K, value:V):boolean
---@return self
function Map:filter(filter) end

---@public
---@generic K, V
---@param self Map<K,V>
---@param filter fun(key:K, value:V):boolean
function Map.filter(self, filter)
    local filtered = {}
    for key, value in pairs(self._map) do
        if filter(key, value) then
            filtered[key] = value
        end
    end
    return Map.new(nil, nil, filtered)
end

---@public
---@generic K,V,C
---@param self Map<K,V>
---@param container C
---@param accumulator fun(container:C, key:K, value:V):void
---@return C
function Map:collect(container, accumulator) end

---@public
---@generic K,V,C
---@param self Map<K,V>
---@param container C
---@param accumulator fun(container:C, key:K, value:V):void
function Map.collect(self, container, accumulator)
    for key, value in pairs(self._map) do
        accumulator(container, key, value)
    end
    return container
end

function test()
    local map = Map.new("", 0, { A = 1, B = 2, C = 3 })
    print("Get")
    local get = map:get("B")
    print(get)

    print("\nfilter.forEach")
    map:filter(function(key, value) return key ~= "A" and value > 2 end)
       :forEach(function(key, value) print(key .. ": " .. value) end)

    print("\nMultimap")
    local multiMap = Map.new("", List.new(0),
                             {
                                 A = List.new(0, { 1 }),
                                 B = List.new(0, { 1, 2 }),
                                 C = List.new(0, { 1, 2, 3 })
                             })
    local list = multiMap
            :filter(function(key, value) return value end)
            :get("B")
            :forEach(function(value) print(value) end)

    print("\nCollect")
    local container = map:collect(List.new(0), function(container, key, value) container:add(value) end)
    container:forEach(function(value) print(value) end)
end

--test()
