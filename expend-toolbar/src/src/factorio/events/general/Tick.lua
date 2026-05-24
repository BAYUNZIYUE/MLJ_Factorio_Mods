import("Event")

---@class Tick : Event
Tick = Event:extendAs("factorio.events.general.Tick")

---@param tick number
function Tick.new(tick)
    return Tick:super(Event.new(tick))
end
