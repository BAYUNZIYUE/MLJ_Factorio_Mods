import("factorio.events.gui.ChangedEvent")

---@class ElementChanged : ChangedEvent
ElementChanged = ChangedEvent:extendAs("factorio.events.gui.ElementChanged")

---@param eventData EventData
function ElementChanged.new(eventData)
    return ElementChanged:super(ChangedEvent.new(eventData))
end
