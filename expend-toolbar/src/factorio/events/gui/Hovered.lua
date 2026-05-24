import("gui.GuiEvent")

---@class Hovered : GuiEvent
Hovered = GuiEvent:extendAs("factorio.events.gui.Hovered")

---@param eventData EventData
function Hovered.new(eventData)
    return Hovered:super(GuiEvent.new(eventData))
end
