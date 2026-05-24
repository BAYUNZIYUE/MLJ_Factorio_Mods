import("gui.toolbar.content.sections.section.content.table.Slot")
import("gui.toolbar.content.sections.section.content.table.slots.tools.simple.SimpleToolButton")
import("factorio.events.events")

---@private
---@class SimpleToolSlot : Slot
SimpleToolSlot = Slot:extendAs("gui.toolbar.content.sections.section.content.table.slots.tools.simple.SimpleToolSlot")

---@public
---@param parent Component
---@param simpleTool SimpleTool
function SimpleToolSlot.create(parent, simpleTool)
    return Slot.create(
            SimpleToolSlot,
            parent,
            function(instance)
                SimpleToolButton.create(instance, simpleTool, { "left", "middle" })
            end
    )
end

function SimpleToolSlot.new(parent, root)
    return SimpleToolSlot:super(Slot.new(parent, root, { SimpleToolButton }))
end

function SimpleToolSlot:initilize()
    SimpleToolSlot:super().initilize(self)

    self:setControls({ [Pick] = function() self:pick() end })

    local eventBus = self:player():eventBus()
    eventBus:subscribeTo(Picked.new(self:thing()), self, function(_) self:button():highlight() end)
    eventBus:subscribeTo(Released.new(self:thing()), self, function(_) self:button():unhighlight() end)
end

---@private
---@return SimpleToolButton
function SimpleToolSlot:button()
    return self:child(SimpleToolButton)
end

function SimpleToolSlot:onClick(click)
    if click:isLeft() then
        self:pick()
    elseif click:isMiddle() then
        self:clear()
    end
end

function SimpleToolSlot:pick()
    self:player():cursor():pickSimpleTool(self:simpleTool())
    self:rememberPick()
end

function SimpleToolSlot:thing()
    return self:simpleTool()
end

---@private
---@return SimpleTool
function SimpleToolSlot:simpleTool()
    return self:button():tool()
end
