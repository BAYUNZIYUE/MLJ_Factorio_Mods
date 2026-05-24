import("Event")

---@class Released : Event
Released = Event:extendAs("player.events.Released")

---@param thing Thing
function Released.new(thing)
    return Released:super(Event.new(thing:id()))
end
