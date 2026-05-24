import("core.Event")

---@class Picked : Event
Picked = Event:extendAs("player.events.Picked")

---@param thing Thing
function Picked.new(thing)
    return Picked:super(Event.new(thing:id()))
end
