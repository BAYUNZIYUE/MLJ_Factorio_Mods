import("factorio.events.gui.ElementChanged")
import("Item")
import("gui.toolbar.content.sections.section.content.table.Slot")
import("gui.toolbar.content.sections.section.content.table.slots.empty.EmptyButton")
import("gui.toolbar.content.sections.section.content.table.slots.item.ItemSlot")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteSlot")
import("gui.toolbar.content.sections.section.content.table.slots.tools.simple.SimpleToolSlot")

---@class EmptySlot : Slot
EmptySlot = Slot:extendAs("gui.toolbar.content.sections.section.content.table.slots.empty.EmptySlot")

function EmptySlot.create(parent)
    return Slot.create(
            EmptySlot,
            parent,
            function(instance)
                EmptyButton.create(instance, { "left", "middle" })
            end
    )
end

function EmptySlot.new(parent, root)
    return EmptySlot:super(Slot.new(parent, root, { EmptyButton }))
end

function EmptySlot:onElementChanged()
    ---@type Cursor
    local cursor = self:player():cursor()
    if cursor:holdsItem() then
        local item = cursor:item()
        self:setItem(item)
        self:handleSlotMove(item)
    elseif cursor:holdsSpidertronRemote() then
        local spidertronRemote = cursor:spidertronRemote()
        self:setSpidertronRemote(spidertronRemote)
        self:handleSlotMove(spidertronRemote)
    elseif cursor:holdsSimpleTool() then
        local simpleTool = cursor:simpleTool()
        self:setSimpleTool(simpleTool)
        self:handleSlotMove(simpleTool)
    elseif cursor:holdsBlueprint() or cursor:holdsPlanner() then
        self:button():clear()
    elseif self:isOccupied() then
        self:setItem(self:item())
    end
end

---@private
---@param thing Thing
function EmptySlot:handleSlotMove(thing)
    ---@type Cursor
    if self:wasMoved(thing) then
        self:move()
    end
    self:player():cursor():clear()
    self:forgetPick()
end

---@private
---@param item Item
function EmptySlot:setItem(item)
    local itemSlot = ItemSlot.create(self:parent(), item)
    self:replaceWith(itemSlot)
    itemSlot:fireTableChange()
end

---@private
---@param spidertronRemote SpidertronRemote
function EmptySlot:setSpidertronRemote(spidertronRemote)
    local spidertronRemoteSlot = SpidertronRemoteSlot.create(self:parent(), spidertronRemote)
    self:replaceWith(spidertronRemoteSlot)
    spidertronRemoteSlot:fireTableChange()
end

---@private
---@param simpleTool SimpleTool
function EmptySlot:setSimpleTool(simpleTool)
    local simpleToolSlot = SimpleToolSlot.create(self:parent(), simpleTool)
    self:replaceWith(simpleToolSlot)
    simpleToolSlot:fireTableChange()
end

function EmptySlot:thing()
    return self:item()
end

---@private
---@return Item
function EmptySlot:item()
    return self:button():item()
end

---@private
---@return EmptyButton
function EmptySlot:button()
    return self:child(EmptyButton)
end
