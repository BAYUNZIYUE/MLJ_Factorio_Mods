import("player.Player")
import("Item")
import("gui.Component")
import("gui.toolbar.Toolbar")
import("gui.toolbar.content.sections.section.content.table.Table")
import("gui.toolbar.content.sections.section.content.table.SlotHistory")

---@class Slot : Component
---@field private __size number
---@field private _toolbar Toolbar
---@field private _history SlotHistory
Slot = Component:extendAs("gui.toolbar.content.sections.section.content.table.Slot")

---@public
---@return number
function Slot:size()
    return Slot.__size
end
Slot.__size = 40

---@protected
---@generic C : Component
---@param class C
---@param parent Component
---@param builder fun(instance: C):void
---@return C
function Slot.create(class, parent, builder)
    return Component.create(
            class,
            parent,
            {
                type = "empty-widget",
                style = "toolbar_content_sections_section_content_table_row_slot"
            },
            builder
    )
end

function Slot.new(parent, element, childrenClasses)
    return Slot:super(Component.new(parent, element, childrenClasses))
end

function Slot:initilize()
    self._history = SlotHistory:getInstanceFor(self:element().player_index)
    self._toolbar = self:ancestor(Toolbar)
end

---@protected
---@param thing Thing
---@return boolean
function Slot:wasMoved(thing)
    return self._history:hasLastPickedSlot() and self._history:lastPickedSlot():isValid()
            and self._history:lastPickedSlot():thing():equals(thing)
end

---@protected
function Slot:move()
    self._history:lastPickedSlot():clear()
end

---@protected
function Slot:rememberPick()
    self._history:rememberPick(self)
end

---@protected
function Slot:forgetPick()
    self._history:forgetPick()
end

---@protected
function Slot:clear()
    local empty = EmptySlot.create(self:parent())
    self:replaceWith(empty)
    empty:fireTableChange()
end

---@protected
function Slot:fireTableChange()
    self._toolbar:tableChanged()
end

---@private
---@return number
function Slot:index()
    return self:element().get_index_in_parent()
end

---@protected
---@return boolean
function Slot:isOccupied()
    return self:thing() ~= nil
end

---@protected
---@return Thing
function Slot:thing()
    error("Not implemented")
end
