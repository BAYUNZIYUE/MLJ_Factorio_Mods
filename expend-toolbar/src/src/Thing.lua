---@class Thing : Object
---@field private _name string
Thing = Object:extendAs("Thing")

---@public
---@param name string
function Thing.new(name)
    local this = Thing:super(Object.new())
    this._name = name
    return this
end

---@public
---@return string
function Thing:id()
    return self._name
end

---@public
---@return string
function Thing:name()
    return self._name
end

---@param other Thing
function Thing:equals(other)
    return self:id() == other:id()
end
