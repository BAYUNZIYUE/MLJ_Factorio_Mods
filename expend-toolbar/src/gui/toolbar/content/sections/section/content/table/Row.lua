import("gui.Component")
import("gui.toolbar.content.sections.section.content.table.slots.empty.EmptySlot")
import("gui.toolbar.content.sections.section.content.table.slots.item.ItemSlot")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteSlot")
import("gui.toolbar.content.sections.section.content.table.slots.tools.simple.SimpleToolSlot")

---@class Row : Component
Row = Component:extendAs("gui.toolbar.content.sections.section.content.table.Row")

function Row.create(parent)
    return Component.create(
            Row,
            parent,
            {
                type = "flow",
                direction = "horizontal",
                style = "toolbar_content_sections_section_content_table_row"
            }
    )
end

function Row.new(parent, root)
    return Row:super(Component.new(parent, root, { EmptySlot, ItemSlot, SpidertronRemoteSlot, SimpleToolSlot }))
end

---@public
---@return boolean
function Row:isOccupied()
    return self:child(ItemSlot) or self:child(SpidertronRemoteSlot) or self:child(SimpleToolSlot)
end

---@public
---@param minimum number
function Row:trimColumnsToMinimum(minimum)
    for _, child in ipairs(self:children()) do
        if child:index() > minimum then
            child:delete()
        end
    end
end

---@public
---@param minimum number
function Row:ensureColumnsMinimum(minimum)
    if self:columnsCount() < minimum then
        local missingColumns = minimum - self:columnsCount()
        local i = 0
        while i < missingColumns do
            EmptySlot.create(self)
            i = i + 1
        end
    end
end

---@public
---@return boolean
function Row:tailHasThing()
    local lastSlot = self:children()[self:columnsCount()]
    return lastSlot and not lastSlot:isInstanceOf(EmptySlot) or false
end

---@public
---@return number
function Row:lastOccupiedColumnIndex()
    local lastOccupiedSlotIndex = 0
    for _, child in ipairs(self:children()) do
        if not child:isInstanceOf(EmptySlot) then
            lastOccupiedSlotIndex = math.max(lastOccupiedSlotIndex, child:index())
        end
    end
    return lastOccupiedSlotIndex
end

---@public
---@return number
function Row:columnsCount()
    return #self:children()
end
