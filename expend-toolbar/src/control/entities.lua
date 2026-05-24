import("factorio.events.entities.SpidertronDeleted")
import("player.Player")

local SpidertronDeletionHandler = {}

---@param event EventData
function SpidertronDeletionHandler.handle(event)
    local spidertronDeleted = SpidertronDeleted.new(event.entity.unit_number)
    for i, player in ipairs(Player.allLoaded()) do
        player:eventBus():publish(spidertronDeleted)
    end
end

script.on_event(
        defines.events.on_player_mined_entity,
        SpidertronDeletionHandler.handle,
        { { filter = "name", name = "spidertron" } }
)

script.on_event(
        defines.events.on_robot_mined_entity,
        SpidertronDeletionHandler.handle,
        { { filter = "name", name = "spidertron" } }
)

script.on_event(
        defines.events.on_entity_died,
        SpidertronDeletionHandler.handle,
        { { filter = "name", name = "spidertron" } }
)

script.on_event(
        defines.events.script_raised_destroy,
        SpidertronDeletionHandler.handle,
        { { filter = "name", name = "spidertron" } }
)
