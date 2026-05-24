import("core.Memento")
import("core.Thing")

---@class SpidertronRemote : Thing
---@field private _unitNumbers number[]
---@field private _id string
---@field private _planetMemento Memento
---@field private _surfaceMemento Memento
---@field private _spidertronsMemento Memento
SpidertronRemote = Thing:extendAs("SpidertronRemote")

---@class SerializedSpidertronRemote
---@field public unitNumbers number[]
SerializedSpidertronRemote = {}

---@public
---@param serializedSpidertronRemote SerializedSpidertronRemote
---@return SpidertronRemote
function SpidertronRemote.deserialize(serializedSpidertronRemote)
    return SpidertronRemote.new(serializedSpidertronRemote.unitNumbers)
end

---@public
---@param unitNumbers number[]
---@return SpidertronRemote
function SpidertronRemote.new(unitNumbers)
    local this = SpidertronRemote:super(Thing.new("spidertron-remote"))
    table.sort(unitNumbers)
    this._unitNumbers = unitNumbers
    this._id = table.concat(this._unitNumbers, ".")
    this._planetMemento = Memento.new(function() return this:freshPlanet() end)
    this._surfaceMemento = Memento.new(function() return this:freshSurface() end)
    this._spidertronsMemento = Memento.new(function() return this:freshSpidertrons() end)
    return this
end

---@public
---@return table
function SpidertronRemote:serialize()
    ---@type SerializedSpidertronRemote
    local serializedSpidertronRemote = {}
    serializedSpidertronRemote.unitNumbers = self._unitNumbers
    return serializedSpidertronRemote
end

---@public
---@return SpidertronRemote
function SpidertronRemote:refreshed()
    local unitNumbers = {}
    for i, spidertron in ipairs(self:spidertrons()) do
        table.insert(unitNumbers, spidertron.unit_number)
    end
    return SpidertronRemote.new(unitNumbers)
end

function SpidertronRemote:id()
    return self._id
end

---@public
---@return LuaPlanet|nil
function SpidertronRemote:planet()
    return self._planetMemento:value()
end

---@private
---@return LuaPlanet|nil
function SpidertronRemote:freshPlanet()
    return self:surface() ~= nil and self:surface().planet or nil
end

---@public
---@return LuaSurface|nil
function SpidertronRemote:surface()
    return self._surfaceMemento:value()
end

---@private
---@return LuaSurface|nil
function SpidertronRemote:freshSurface()
    local firstUnitNumber = self._unitNumbers[1]
    if firstUnitNumber ~= nil then
        local firstSpidertron = game.get_entity_by_unit_number(firstUnitNumber)
        if firstSpidertron then
            return firstSpidertron.surface
        else
            return nil
        end
    else
        return nil
    end
end

---@public
---@param unitNumberToExclude number
---@return SpidertronRemote
function SpidertronRemote:withExcludedUnit(unitNumberToExclude)
    local newUnitNumbers = {}
    for i, unitNumber in ipairs(self._unitNumbers) do
        if unitNumber ~= unitNumberToExclude then
            table.insert(newUnitNumbers, unitNumber)
        end
    end
    return SpidertronRemote.new(newUnitNumbers)
end

---@public
---@return number
function SpidertronRemote:unitsCount()
    return #self._unitNumbers
end

---@public
---@return number[]
function SpidertronRemote:unitNumbers()
    return self._unitNumbers
end

---@public
---@return boolean
function SpidertronRemote:hasSpidertrons()
    return self:spidertrons()[1] ~= nil
end

---@public
---@return LuaEntity|nil
function SpidertronRemote:firstSpidertron()
    return self:spidertrons()[1]
end

---@public
---@return LuaEntity[]
function SpidertronRemote:spidertrons()
    return self._spidertronsMemento:value()
end

---@private
---@return LuaEntity[]
function SpidertronRemote:freshSpidertrons()
    local spidertrons = {}
    for i, unitNumber in ipairs(self._unitNumbers) do
        local spidertron = game.get_entity_by_unit_number(unitNumber)
        if spidertron then
            table.insert(spidertrons, spidertron)
        end
    end
    return spidertrons
end
