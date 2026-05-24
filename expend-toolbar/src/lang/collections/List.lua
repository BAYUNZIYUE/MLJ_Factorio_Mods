if false then
    require("lang.Object")
    require("lang.collections.Map")
end

---@generic V
---@class List : Object
---@field _list V[]
List = Object:extendAs("lang.collections.List")

---@public
---@generic V
---@param valueType V
---@param list V[] optional
---@return List<V>
function List.new(valueType, list)
    local this = List:super(Object.new())
    this._list = list and list or {}
    return this
end

---@generic V
---@param self List<V>
---@param element V
function List:add(element)
    table.insert(self._list, element)
end

---@generic V
---@param self List<V>
---@param element V
function List.add(self, element)
    table.insert(self._list, element)
end

---@public
---@generic V
---@param value V
---@return boolean
function List:contains(value)
    for i, v in ipairs(self._list) do
        if v == value then
            return true
        end
    end
    return false
end

---@public
---@return boolean
function List:isEmpty()
    return self._list[1] == nil
end

---@public
---@generic V
---@param self List<V>
---@param consumer fun(value:V):void
function List:forEach(consumer) end

---@public
---@generic V
---@param self List<V>
---@param consumer fun(value:V):void
function List.forEach(self, consumer)
    for index, value in ipairs(self._list) do
        consumer(value)
    end
end

---@public
---@generic V, R
---@param self List<V>
---@param mapper fun(value:V):R
---@return List<R>
function List:map(mapper) end

---@public
---@generic V, R
---@param self List<V>
---@param mapper fun(value:V):R
function List.map(self, mapper)
    local mapped = {}
    for index, value in ipairs(self._list) do
        table.insert(mapped, mapper(value))
    end
    return List.new(nil, mapped)
end

---@public
---@generic V, R
---@param self List<V>
---@param filter fun(value:V):boolean
---@return self
function List:filter(filter) end

---@public
---@generic V, R
---@param self List<V>
---@param filter fun(value:V):boolean
function List.filter(self, filter)
    local filtered = {}
    for index, value in ipairs(self._list) do
        if filter(value) then
            table.insert(filtered, value)
        end
    end
    return List.new(nil, filtered)
end

---@public
---@generic V
---@param self List<V>
---@param identity V
---@param accumulator fun(first:V, second:V):V
---@return V
function List:foldLeft(identity, accumulator) end

---@public
---@generic V
---@param self List<V>
---@param identity V
---@param accumulator fun(first:V, second:V):V
function List.foldLeft(self, identity, accumulator)
    local result = identity
    for index, value in ipairs(self._list) do
        result = accumulator(result, value)
    end
    return result
end

---@public
---@generic V,C
---@param self List<V>
---@param container C
---@param accumulator fun(container:C, value:V):void
---@return C
function List:collect(container, accumulator) end

---@public
---@generic V,C
---@param self List<V>
---@param container C
---@param accumulator fun(container:C, value:V):void
function List.collect(self, container, accumulator)
    for index, value in ipairs(self._list) do
        accumulator(container, value)
    end
    return container
end

function test()
    print("Map.filter.forEach")
    List.new("", { "A", "AA", "AAA" })
        :map(function(value) return value end)
        :map(function(value) return value end)
        :filter(function(value) return value:len() > 1 end)
        :map(function(value) return value:len() end)
        :forEach(function(value) print(value) end)

    print("\nFoldLeft")
    local folded = List.new(0, { 1, 3, 5 }):foldLeft(0, function(first, second) return first + second end)
    print(folded)
    assert(folded == 9)

    print("\nCollect")
    List.new("", { "A", "AA", "AAA" })
        :collect(List.new(0), function(container, value) container = container:add(value:len()) end)
        :forEach(function(value) print(value) end)
end

--test()
