import("player.inventory.ViewInventory")
import("player.inventory.remote.space_platform.SpacePlatformHubMainInventory")
import("player.inventory.remote.space_platform.SpacePlatformHubTrashInventory")

---@class SpacePlatformViewInventory : ViewInventory
---@field private _player Player
SpacePlatformViewInventory = ViewInventory:extendAs("player.inventory.remote.space_platform.SpacePlatformViewInventory")

---@public
---@param player Player
---@param initialContent Content
---@return SpacePlatformViewInventory
function SpacePlatformViewInventory.new(player, initialContent)
    return SpacePlatformViewInventory:super(
            ViewInventory.new(
                    player,
                    initialContent,
                    {
                        SpacePlatformHubMainInventory.new(player),
                        SpacePlatformHubTrashInventory.new(player),
                    },
                    {}
            )
    )
end
