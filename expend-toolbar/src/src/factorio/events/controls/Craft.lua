import("Event")

---@class Craft : Event
---@field private _one boolean
---@field private _five boolean
---@field private _stackHalf boolean
---@field private _stack boolean
---@field private _allHalf boolean
---@field private _all boolean
Craft = Event:extendAs("factorio.events.controls.Craft")

---@public
---@return Craft
function Craft:one()
    local craft = Craft.new()
    craft._one = true
    return craft
end

---@public
---@return Craft
function Craft:five()
    local craft = Craft.new()
    craft._five = true
    return craft
end

---@public
---@return Craft
function Craft:stackHalf()
    local craft = Craft.new()
    craft._stackHalf = true
    return craft
end

---@public
---@return Craft
function Craft:stack()
    local craft = Craft.new()
    craft._stack = true
    return craft
end

---@public
---@return Craft
function Craft:allHalf()
    local craft = Craft.new()
    craft._allHalf = true
    return craft
end

---@public
---@return Craft
function Craft:all()
    local craft = Craft.new()
    craft._all = true
    return craft
end

---@private
---@return Craft
function Craft.new()
    return Craft:super(Event.new())
end

---@public
---@return boolean
function Craft:isOne()
    return self._one ~= nil
end

---@public
---@return boolean
function Craft:isFive()
    return self._five ~= nil
end

---@public
---@return boolean
function Craft:isStackHalf()
    return self._stackHalf ~= nil
end

---@public
---@return boolean
function Craft:isStack()
    return self._stack ~= nil
end

---@public
---@return boolean
function Craft:isAllHalf()
    return self._allHalf ~= nil
end

---@public
---@return boolean
function Craft:isAll()
    return self._all ~= nil
end
