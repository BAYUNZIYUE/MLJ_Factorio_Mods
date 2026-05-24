import("gui.GuiEvent")

---@class Left : GuiEvent
Left = GuiEvent:extendAs("factorio.events.gui.Left")

---@param eventData EventData
function Left.new(eventData)
    return Left:super(GuiEvent.new(eventData))
end
