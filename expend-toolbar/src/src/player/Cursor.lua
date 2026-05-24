import("Item")
import("Nothing")
import("SimpleTool")
import("SpidertronRemote")

---@class Cursor : Object
---@field private _luaPlayer LuaPlayer
---@field private _currentThing Thing
---@field private _currentThingCount number
---@field private _previousThing number
---@field private _previousThingCount number
Cursor = Object:extendAs("player.Cursor")

---@return Cursor
---@param luaPlayer LuaPlayer
function Cursor.new(luaPlayer)
    local this = Cursor:super(Object.new())
    this._luaPlayer = luaPlayer
    this._previousThing = Nothing.new()
    this._previousThingCount = 0
    this._currentThing = this:getCurrentThing()
    this._currentThingCount = 0
    return this
end

---@public
function Cursor:refresh()
    self._previousThing = self._currentThing
    self._previousThingCount = self._currentThingCount
    self._currentThing = self:getCurrentThing()
    self._currentThingCount = self:getCurrentThingCount()
end

---@private
---@return Thing
function Cursor:getCurrentThing()
    if self:holdsItem() then
        return self:item()
    elseif self:holdsSpidertronRemote() then
        return self:spidertronRemote()
    elseif self:holdsSimpleTool() then
        return self:simpleTool()
    else
        return Nothing.new()
    end
end

---@private
---@return number
function Cursor:getCurrentThingCount()
    if self:holdsStack() then
        return self:stackCount()
    else
        return 0
    end
end

---@public
---@return Thing
function Cursor:previousThing()
    return self._previousThing
end

---@public
---@return number
function Cursor:previousThingCount()
    return self._previousThingCount
end

---@public
---@return Thing
function Cursor:currentThing()
    return self._currentThing
end

function Cursor:currentThingCount()
    return self._currentThingCount
end

---@public
---@return boolean
function Cursor:holdsItem()
    return self:holdsThing() and not self:holdsSpidertronRemote() and not self:holdsTool()
end

---@public
---@return boolean
function Cursor:holdsSpidertronRemote()
    return self:holdsThing() and self:thingName() == "spidertron-remote"
end

---@public
---@return boolean
function Cursor:holdsTool()
    return self:holdsThing() and (self:holdsSimpleTool() or self:holdsBlueprint() or self:holdsPlanner())
end

---@public
---@return boolean
function Cursor:holdsSimpleTool()
    return self:holdsThing()
            and (
            self:thingType() == "selection-tool"
                    or self:thingType() == "copy-paste-tool"
                    or self:thingName() == "green-wire"
                    or self:thingName() == "red-wire"
                    or self:thingName() == "copper-wire"
                    or self:thingName() == "artillery-targeting-remote"
                    or self:thingName() == "discharge-defense-remote"
                    or self:thingName() == "spidertron-remote"
    )
end

---@public
---@return boolean
function Cursor:holdsBlueprint()
    return self:holdsThing() and self._luaPlayer.is_cursor_blueprint()
end

---@public
---@return boolean
function Cursor:holdsPlanner()
    return self:holdsThing() and (self:thingType() == "deconstruction-item" or self:thingType() == "upgrade-item")
end

---@private
---@return boolean
function Cursor:holdsThing()
    return not self._luaPlayer.is_cursor_empty() and (self:holdsStack() or self:holdsGhost())
end

function Cursor:thingName()
    if self:holdsStack() then
        return self._luaPlayer.cursor_stack.name
    elseif self:holdsGhost() then
        return self._luaPlayer.cursor_ghost.name
    else
        error("Called for a thing name when the cursor is empty")
    end
end

function Cursor:thingType()
    if self:holdsStack() then
        return self._luaPlayer.cursor_stack.type
    elseif self:holdsGhost() then
        return self._luaPlayer.cursor_ghost
    else
        error("Called for a thing type when the cursor is empty")
    end
end

---@public
---@return SimpleTool
function Cursor:simpleTool()
    if self:holdsSimpleTool() then
        return SimpleTool.new(self._luaPlayer.cursor_stack.name)
    else
        error("Called for a simple tool when the cursor is not holding a simple tool")
    end
end

---@public
---@return Item
function Cursor:item()
    if self:holdsItem() then
        if self:holdsStack() then
            local stack = self._luaPlayer.cursor_stack
            return Item.new(stack.name, stack.quality.name)
        elseif self:holdsGhost() then
            local ghost = self._luaPlayer.cursor_ghost
            return Item.new(ghost.name.name, ghost.quality and ghost.quality.name or nil)
        else
            error("Called for an item when the cursor is empty")
        end
    else
        error("Called for an item when the cursor is not holding an item")
    end
end

---@public
---@return Item
function Cursor:spidertronRemote()
    if self:holdsSpidertronRemote() then
        ---@type LuaItemStack
        local stack = self._luaPlayer.cursor_stack
        local itemNumber = stack.item_number
        local unitNumbers = {}
        if self._luaPlayer.spidertron_remote_selection then
            for i, entity in ipairs(self._luaPlayer.spidertron_remote_selection) do
                table.insert(unitNumbers, entity.unit_number)
            end
        end
        return SpidertronRemote.new(unitNumbers)
    else
        error("Called for a spidertron remote when the cursor is not holding a spidertron remote")
    end
end

---@public
---@return boolean
function Cursor:holdsStack()
    local stack = self:stack()
    return stack and stack.valid_for_read and stack.name
end

---@public
---@return number
function Cursor:stackCount()
    return self:stack().count
end

---@public
---@return LuaItemStack
function Cursor:stack()
    return self._luaPlayer.cursor_stack
end

---@public
---@param stack LuaItemStack
---@return boolean successful
function Cursor:pickStack(stack)
    self:clear()
    return self._luaPlayer.cursor_stack.transfer_stack(stack)
end

---@public
---@return boolean
function Cursor:holdsGhost()
    return self._luaPlayer.cursor_ghost and self._luaPlayer.cursor_ghost.name
end

---@public
---@param item Item
function Cursor:pickGhost(item)
    self:clear()
    self._luaPlayer.cursor_ghost = item:nameQualityPair()
end

---@public
---@param spidertronRemote SpidertronRemote
function Cursor:pickSpidertronRemote(spidertronRemote)
    self:clear()
    self._luaPlayer.cursor_stack.set_stack { name = "spidertron-remote", count = 1 }
    self._luaPlayer.spidertron_remote_selection = spidertronRemote:spidertrons()
end

---@public
---@param simpleTool SimpleTool
function Cursor:pickSimpleTool(simpleTool)
    self:clear()
    self._luaPlayer.cursor_stack.set_stack { name = simpleTool:name(), count = 1 }
end

---@public
function Cursor:clear()
    self._luaPlayer.clear_cursor()
end
