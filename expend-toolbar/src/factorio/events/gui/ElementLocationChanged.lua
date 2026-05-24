import("factorio.events.gui.ChangedEvent")

---@class ElementLocationChanged : ChangedEvent
ElementLocationChanged = ChangedEvent:extendAs("factorio.events.gui.ElementLocationChanged")

---@param eventData EventData
function ElementLocationChanged.new(eventData)
    return ElementLocationChanged:super(ChangedEvent.new(eventData))
end
