import("factorio.LocalisedText")
import("factorio.RichText")
import("factorio.TechnologyPrototypes")
import("factorio.QualityLevels")
import("player.inventory.InventoryChanged")

---@class Tooltip : Object
---@field private _ table
---@field private _player Player
---@field private _slot ItemSlot
---@field private _upToDate boolean
---@field private _inventoryRequester table
---@field private _showRequester table
---@field private _refreshRequester table
Tooltip = Object:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.Tooltip")

---@public
---@param player Player
---@param slot ItemSlot
---@return Tooltip
function Tooltip.new(player, slot)
    local this = Tooltip:super(Object.new())
    this._player = player
    this._slot = slot
    this._upToDate = false
    this._inventoryRequester = {}
    this._showRequester = {}
    this._refreshRequester = {}
    return this
end

function Tooltip:onHover()
    self._player:scheduler():schedule(
            self._inventoryRequester,
            self._player:settings():tooltipDelay() - 1,
            function()
                self._player:eventBus():subscribeTo(InventoryChanged, self, function()
                    self._upToDate = false
                end)
            end
    )
    self._player:scheduler():schedule(
            self._showRequester,
            self._player:settings():tooltipDelay(),
            function()
                self:show()
            end
    )
    self:scheduleRefresh()
end

function Tooltip:scheduleRefresh()
    self._player:scheduler():schedule(
            self._refreshRequester,
            self._player:settings():tooltipRefreshInterval(),
            function()
                self:refresh()
                self:scheduleRefresh()
            end
    )
end

function Tooltip:onLeave()
    self._player:scheduler():cancelAll(self._inventoryRequester)
    self._player:scheduler():cancelAll(self._showRequester)
    self._player:scheduler():cancelAll(self._refreshRequester)
    self._player:eventBus():unsubscribeFromAll(self)
    self._slot:hideTooltips()
end

---@public
function Tooltip:refresh()
    if not self._upToDate and self:isVisible() then
        self:show()
        self._upToDate = true
    end
end

---@private
---@return boolean
function Tooltip:isVisible()
    return self._slot:tooltipsAreVisible()
end

---@private
function Tooltip:show()
    self._slot:showTooltips(self:localisedString())
end

function Tooltip:localisedString()
    if #self._player:viewInventory():mains() > 0 or #self._player:viewInventory():sides() > 0 then
        return LocalisedText.new()
                            :concat(self:createInventory())
                            :concat(self:createBiggestCraftingPlan())
                            :concat(self:createControls())
                            :localisedString()
    else
        return nil
    end
end

---@private
---@return LocalisedText
function Tooltip:createInventory()
    local inventoryText = LocalisedText.new()
                                       :append(RichText.fontMonospacedStart())
                                       :concat(self:createHeader())
                                       :concat(self:createTable())
    return inventoryText:append(RichText.fontEnd())
end

---@private
---@return LocalisedText
function Tooltip:createHeader()
    local itemName = self._slot:item():name()
    local headerText = LocalisedText.new()

    for i, main in ipairs(self._player:viewInventory():mains()) do
        if main:alwaysVisible() or main:content():hasItem(itemName) then
            headerText
                    :append("  ")
                    :append(RichText.fontMonospacedIcon3Spaces(main:icon():richText()))
                    :append(RichText.iconEmpty())
        end
    end

    for i, side in ipairs(self._player:viewInventory():sides()) do
        if side:alwaysVisible() or side:content():hasItem(itemName) then
            headerText
                    :append("  ")
                    :append(RichText.fontMonospacedIcon3Spaces(side:icon():richText()))
                    :append(RichText.iconEmpty())
        end
    end

    return headerText
end

---@private
---@return LocalisedText
function Tooltip:createTable()
    local tableText = LocalisedText.new()

    local itemName = self._slot:item():name()
    local anyHas = false
    local allQualitiesCounts = {}
    local mainsQualitiesCounts = {}
    for _, main in ipairs(self._player:viewInventory():mains()) do
        local has = main:content():hasItem(itemName)
        anyHas = anyHas or has
        if main:alwaysVisible() or has then
            table.insert(allQualitiesCounts, main:content():allQualitiesCount(itemName))
            table.insert(mainsQualitiesCounts, main:content():allQualitiesCount(itemName))
        end
    end
    local sidesQualitiesCounts = {}
    for _, side in ipairs(self._player:viewInventory():sides()) do
        local has = side:content():hasItem(itemName)
        anyHas = anyHas or has
        if side:alwaysVisible() or has then
            table.insert(allQualitiesCounts, side:content():allQualitiesCount(itemName))
            table.insert(sidesQualitiesCounts, side:content():allQualitiesCount(itemName))
        end
    end

    if not anyHas then
        tableText:appendNewLine()
        tableText:concat(self:createNullRow(#mainsQualitiesCounts + #sidesQualitiesCounts))
    else
        for i, qualityName in ipairs(self:allSortedQualitiesOf(allQualitiesCounts)) do
            tableText:appendNewLine()
                     :concat(self:createRow(qualityName, mainsQualitiesCounts, sidesQualitiesCounts))
        end
    end

    return tableText
end

---@private
---@param columnsCount number
---@return LocalisedText
function Tooltip:createNullRow(columnsCount)
    local nullRowText = LocalisedText.new()
    for i = 1, columnsCount do
        nullRowText:concat(Tooltip._.inventory.nullCell)
                   :append(" ")
    end
    return nullRowText
end

---@private
---@param allQualitiesCounts table<string, number>[]
---@return string[]
function Tooltip:allSortedQualitiesOf(allQualitiesCounts)
    local allQualities = {}
    for _, allQualitiesCount in ipairs(allQualitiesCounts) do
        for qualityName, _ in pairs(allQualitiesCount) do
            if prototypes.quality[qualityName] then
                allQualities[qualityName] = QualityLevels.instance():getQualityLevel(qualityName)
            end
        end
    end

    local allSortedQualitiesEntries = {}
    for name, level in pairs(allQualities) do
        table.insert(allSortedQualitiesEntries, { name = name, level = level })
    end
    table.sort(allSortedQualitiesEntries, function(first, second) return first.level > second.level end)

    ---@type string[]
    local allSortedQualities = {}
    for i, quality in ipairs(allSortedQualitiesEntries) do
        table.insert(allSortedQualities, quality.name)
    end

    return allSortedQualities
end

---@private
---@return LocalisedText
---@param qualityName string
---@param mainsQualitiesCounts table<string, number>[]
---@param sidesQualitiesCounts table<string, number>[]
function Tooltip:createRow(qualityName, mainsQualitiesCounts, sidesQualitiesCounts)
    local rowText = LocalisedText.new()

    for i, mainQualitiesCount in ipairs(mainsQualitiesCounts) do
        rowText:concat(self:createCell(qualityName, mainQualitiesCount[qualityName]))
               :append(RichText.monospace())
    end

    for i, sideQualitiesCount in ipairs(sidesQualitiesCounts) do
        if next(sideQualitiesCount) then
            rowText:concat(self:createCell(qualityName, sideQualitiesCount[qualityName]))
                   :append(RichText.monospace())
        end
    end

    return rowText
end

---@private
---@param qualityName string
---@param qualityCount number | nil
---@return LocalisedText
function Tooltip:createCell(qualityName, qualityCount)
    if qualityCount then
        if self._slot:item():quality() == qualityName then
            return LocalisedText.new()
                                :append(RichText.countColumn(qualityCount))
                                :append(RichText.icon("quality", qualityName))
        else
            return LocalisedText.new()
                                :append(RichText.colorGray(RichText.countColumn(qualityCount)))
                                :append(RichText.icon("quality", qualityName))
        end
    else
        return Tooltip._.inventory.emptyCell
    end
end

---@private
---@return LocalisedText
function Tooltip:createBiggestCraftingPlan()
    if self._player:settings():crafting() then
        local biggestCraftingPlan = self._player:viewInventory():craftingPlansInDescendingCountOrderForAnItem(self._slot:item():name())[1]
        if biggestCraftingPlan then
            return biggestCraftingPlan:fullDescription()
        else
            return LocalisedText.empty()
        end
    else
        return LocalisedText.empty()
    end
end

---@protected
---@return LocalisedText
function Tooltip:createControls()
    if self._player:settings():showControlsInTheTooltip() then
        if self._player:settings():crafting() then
            return Tooltip._.controls.withCrafting
        else
            return Tooltip._.controls.withoutCrafting
        end
    else
        return LocalisedText.empty()
    end
end

Tooltip._ = {}
Tooltip._.inventory = {}
Tooltip._.inventory.nullCell = LocalisedText.new()
                                            :append("   ø")
                                            :append(RichText.iconEmpty())
Tooltip._.inventory.emptyCell = LocalisedText.new()
                                             :append("    ")
                                             :append(RichText.iconEmpty())

Tooltip._.controls = {}
Tooltip._.controls.common = LocalisedText
        .new()
        :appendNewLine()
        :append("________________________________")
        :appendNewLine()

--:append({ "key-sequences.open-factoriopedia" })
--:append(RichText.keySequence(": "))
--:append({ "controls.open-factoriopedia" })

        :append({ "key-sequences.cycle-quality-up" })
        :append(RichText.keySequence(": "))
        :append({ "controls.cycle-quality-up" })
        :appendNewLine()

        :append({ "key-sequences.cycle-quality-down" })
        :append(RichText.keySequence(": "))
        :append({ "controls.cycle-quality-down" })

Tooltip._.controls.crafting = LocalisedText
        .new()
        :append({ "key-sequences.craft" })
        :append(RichText.keySequence(": "))
        :append({ "controls.craft" })
        :appendNewLine()

        :append({ "key-sequences.craft-5" })
        :append(RichText.keySequence(": "))
        :append({ "controls.craft-5" })
        :appendNewLine()

        :append({ "key-sequences.stack-transfer" })
        :append(RichText.keySequence(": "))
        :append({ "gui-permissions-names.Craft" })
        :append(" ")
        :append({ "description.stack-size" })
        :appendNewLine()

        :append({ "key-sequences.stack-split" })
        :append(RichText.keySequence(": "))
        :append({ "gui-permissions-names.Craft" })
        :append(" ")
        :append({ "description.stack-size" })
        :append("/2")
        :appendNewLine()

        :append({ "key-sequences.craft-all" })
        :append(RichText.keySequence(": "))
        :append({ "controls.craft-all" })
        :appendNewLine()

        :append({ "key-sequences.inventory-split" })
        :append(RichText.keySequence(": "))
        :append({ "controls.craft-all" })
        :append("/2")

Tooltip._.controls.settingsHint = LocalisedText
        .new()
        :append(RichText.fontSmall("(hide controls in settings)"))

Tooltip._.controls.withCrafting = LocalisedText
        .new()
        :concat(Tooltip._.controls.common)
        :appendNewLine()
        :appendNewLine()
        :concat(Tooltip._.controls.crafting)
        :appendNewLine()
        :concat(Tooltip._.controls.settingsHint)

Tooltip._.controls.withoutCrafting = LocalisedText
        .new()
        :concat(Tooltip._.controls.common)
        :appendNewLine()
        :concat(Tooltip._.controls.settingsHint)
