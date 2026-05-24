import("gui.GuiEvent")

---@class ChangedEvent : GuiEvent
ChangedEvent = GuiEvent:extendAs("factorio.events.gui.ChangedEvent")

---@param eventData EventData
function ChangedEvent.new(eventData)
    return ChangedEvent:super(GuiEvent.new(eventData))
end
