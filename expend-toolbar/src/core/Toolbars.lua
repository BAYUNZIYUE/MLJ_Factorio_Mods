require("lang._package")
import("gui.Box")

---@class Toolbars
---@field public loaded boolean
---@field public name string
---@field public controls table<string, string>
---@field public icons table<string, string>
---@field public styles table<string, table>
Toolbars = {}
Toolbars.name = "expend-toolbar"
Toolbars.loaded = false

---@public
---@param name string
---@return string
function Toolbars.prefix(name)
    return Toolbars.name .. "_" .. name
end

Toolbars.controls = {
    pipette = Toolbars.prefix("pipette"),
    toggleFilter = Toolbars.prefix("toggle-filter"),
    openFactoriopedia = Toolbars.prefix("open-factoriopedia"),
    increaseQuality = Toolbars.prefix("increase-quality"),
    decreaseQuality = Toolbars.prefix("decrease-quality"),
    createToolbar = Toolbars.prefix("create-toolbar"),
    toggleToolbars = Toolbars.prefix("toggle-toolbars"),
    toggleToolbarHeader = Toolbars.prefix("toggle-toolbar-header"),
}

Toolbars.icons = {
    one = Toolbars.prefix("1"),
    alignToolbarTop = Toolbars.prefix("align-toolbar-top"),
    alignToolbarBottom = Toolbars.prefix("align-toolbar-bottom"),
    cancel = Toolbars.prefix("cancel"),
    collapseUpward = Toolbars.prefix("collapse-upward"),
    collapseDownward = Toolbars.prefix("collapse-downward"),
    confirm = Toolbars.prefix("confirm"),
    expand = Toolbars.prefix("expand"),
    moveSectionDown = Toolbars.prefix("move-section-down"),
    moveSectionUp = Toolbars.prefix("move-section-up"),
    padlockClosed = Toolbars.prefix("padlock-closed"),
    padlockOpen = Toolbars.prefix("padlock-open"),

    empty = Toolbars.prefix("empty"),

    characterTrash = Toolbars.prefix("character-trash"),
    carTrash = Toolbars.prefix("car-trash"),
    tankTrash = Toolbars.prefix("tank-trash"),
    spidertronTrash = Toolbars.prefix("spider-trash"),
    spacePlatformHubTrash = Toolbars.prefix("space-platform-hub-trash"),
}

Toolbars.settings = {
    columns = "columns",
    tooltipDelay = "tooltip-delay",
    tooltipRefreshInterval = "tooltip-refresh-interval",
    showControlsInTheTooltip = "show-controls-in-the-tooltip",
    characterInventoriesContentRefreshInterval = "character-inventories-content-refresh-interval",
    showVehicleInventoriesContent = "show-vehicle-inventories-content",
    vehicleInventoriesContentRefreshInterval = "vehicle-inventories-content-refresh-interval",
    showLogisticNetworksContent = "show-logistic-networks-content",
    logisticNetworksContentRefreshInterval = "logistic-networks-content-refresh-interval",
}

Toolbars.styles = {
    common = {
        button = {
            box = Box.new():withContentSize(20)
        }
    },
    toolbar = {
        box = Box.new():withBorder(4),
        spacing = 2,

        content = {
            sections = {
                spacing = 1,

                section = {
                    box = Box.new():withBorder(4),

                    header = {
                        box = Box.new():withBottomMargin(1),

                        button = {
                            box
                        }
                    },
                    content = {
                        box = Box.new():withTopMargin(2)
                    }
                }
            },
            addSection = {
                box = Box.new():withHeight(20)
            }
        },
    },
}
