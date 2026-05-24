import("Item")
import("factorio.ItemFluidPrototypes")
import("factorio.events.general.ControllerChanged")
import("player.PlayerSettings")
import("player.events.CharacterInventoryChanged")
import("player.inventory.ViewInventoryItemCountChanged")
import("player.events.Picked")
import("player.events.Released")
import("factorio.events.controls.Clear")
import("factorio.events.controls.Craft")
import("factorio.events.controls.DecreaseQuality")
import("factorio.events.controls.IncreaseQuality")
import("factorio.events.controls.OpenFactoriopedia")
import("factorio.events.controls.Pick")
import("factorio.events.controls.SearchFactory")
import("gui.toolbar.content.sections.section.content.table.Slot")
import("gui.toolbar.content.sections.section.content.table.slots.item.CountOverlay")
import("gui.toolbar.content.sections.section.content.table.slots.item.DimOverlay")
import("gui.toolbar.content.sections.section.content.table.slots.item.ItemButton")
import("gui.toolbar.content.sections.section.content.table.slots.item.QualityOverlay")
import("gui.toolbar.content.sections.section.content.table.slots.item.Tooltip")

---@class ItemSlot : Slot
---@field private _item Item
---@field private _tooltip Tooltip
ItemSlot = Slot:extendAs("gui.toolbar.content.sections.section.content.table.slots.item.ItemSlot")

---@param parent Component
---@param item Item
function ItemSlot.create(parent, item)
    return Slot.create(
            ItemSlot,
            parent,
            function(instance)
                local tags = instance:element().tags
                tags.item = { name = item:name(), quality = item:quality() }
                instance:element().tags = tags

                ItemButton.create(instance, item, { "left", "middle", "right", "button-5" })
                QualityOverlay.create(instance)
                CountOverlay.create(instance)
                DimOverlay.create(instance)
            end
    )
end

function ItemSlot.new(parent, root)
    return ItemSlot:super(Slot.new(parent, root, {
        ItemButton, QualityOverlay, CountOverlay, DimOverlay
    }))
end

function ItemSlot:propagateInitialization()
    if self:migrateTo_2_32_0() then return end
    ItemSlot:super().propagateInitialization(self)
end

---@private
---@return boolean Slot was deleted
function ItemSlot:migrateTo_2_32_0()
    if self:element().tags.item == nil then
        if self:button():element().elem_tooltip == nil then
            self:replaceWith(EmptySlot.create(self:parent()))
            return true
        else
            local elemTooltip = self:button():element().elem_tooltip
            local tags = self:element().tags
            tags.item = { name = elemTooltip.name, quality = elemTooltip.quality }
            self:element().tags = tags
            self:button():element().elem_tooltip = nil
            return false
        end
    else
        return false
    end
end

function ItemSlot:initilize()
    ItemSlot:super().initilize(self)
    self._item = self:loadItem()

    if self:deleteIfTheItemIsUnknown() then return end

    self:migrateTo_2_21_0()
    self:migrateTo_2_23_0()

    self:qualityOverlay():refresh()
    self:countOverlay():refresh()
    self:dimOverlay():refresh()

    self._tooltip = Tooltip.new(self:player(), self)

    self:setControls(
            {
                [Pick] = function() self:handlePick() end,
                [Clear] = function() self:handleClear() end,
                [OpenFactoriopedia] = function() self:openInFactoriopedia() end,
                [Craft] = function(craft) self:handleCraft(craft) end,
                [IncreaseQuality] = function() self:increaseQuality() end,
                [DecreaseQuality] = function() self:decreaseQuality() end,
                [SearchFactory] = function() self:searchFactory() end,
            }
    )

    self:subscribeToPickRelease()

    self:player():eventBus()
        :subscribeTo(ViewInventoryItemCountChanged.new(self._item:name()), self:countOverlay(), function()
        self:countOverlay():refresh()
        self:dimOverlay():refresh()
    end)
end

---@private
---@param item Item
function ItemSlot:setItem(item)
    local tags = self:element().tags
    tags.item = { name = item:name(), quality = item:quality() }
    self:element().tags = tags

    self:unsubscribeFromPickRelease()
    self._item = self:loadItem()
    self:subscribeToPickRelease()
end

---@private
function ItemSlot:subscribeToPickRelease()
    self:player():eventBus():subscribeTo(Picked.new(self._item), self, function()
        self:button():highlight()
    end)
    self:player():eventBus():subscribeTo(Released.new(self._item), self, function()
        self:button():unhighlight()
    end)
end

---@private
function ItemSlot:unsubscribeFromPickRelease()
    self:player():eventBus():unsubscribeFrom(Picked.new(self._item), self)
    self:player():eventBus():unsubscribeFrom(Released.new(self._item), self)
end

---@private
---@return Item
function ItemSlot:loadItem()
    local itemTag = self:element().tags.item
    return Item.new(itemTag.name, itemTag.quality)
end

---@private
---@return boolean
function ItemSlot:deleteIfTheItemIsUnknown()
    if ItemFluidPrototypes.instance():findItemFluidPrototype(self._item:name()) == nil then
        Log.log("Unknown item slot deleted: " .. self._item:name())
        self:replaceWith(EmptySlot.create(self:parent()))
        return true
    else
        return false
    end
end

---@private
function ItemSlot:migrateTo_2_21_0()
    self:button():element().number = nil
    if not self:countOverlay() then
        CountOverlay.create(self)
    end
end

---@private
function ItemSlot:migrateTo_2_23_0()
    if not self:dimOverlay() then
        DimOverlay.create(self)
    end
end

function ItemSlot:onClick(click)
    if click:isLeft() and not click:withModifier() then
        self:handlePick()
    end
end

---@private
function ItemSlot:handlePick()
    self:player():viewInventory():pick(self._item)
    self:rememberPick()
    self:presentSuccess()
end

---@private
function ItemSlot:handleClear()
    self:clear()
    self:presentSuccess()
end

---@private
function ItemSlot:openInFactoriopedia()
    self:player():luaPlayer().open_factoriopedia_gui(ItemFluidPrototypes.instance():findItemFluidPrototype(self:item():name()))
end

---@private
---@param craft Craft
function ItemSlot:handleCraft(craft)
    if self:player():settings():crafting() and self:player():inCharacterView() then
        local biggestCraftingPlan = self:player():viewInventory():craftingPlansInDescendingCountOrderForAnItem(self._item:name())[1]
        if biggestCraftingPlan then
            local startedCraftingCount = biggestCraftingPlan:execute(self:calculateCraftCount(craft,
                                                                                              biggestCraftingPlan))
            if startedCraftingCount > 0 then
                self:presentSuccess(startedCraftingCount)
            else
                self:presentFailure(startedCraftingCount)
            end
        else
            self:presentFailure("-")
        end
    end
end

---@private
---@param craft Craft
---@param craftingPlan CraftingPlan
function ItemSlot:calculateCraftCount(craft, craftingPlan)
    if craft:isOne() then
        return 1
    elseif craft:isFive() then
        return 5
    elseif craft:isStackHalf() then
        return self:itemPrototype().stack_size / 2
    elseif craft:isStack() then
        return self:itemPrototype().stack_size
    elseif craft:isAllHalf() then
        return craftingPlan:craftableCountOf(self._item:name()) / 2
    elseif craft:isAll() then
        return craftingPlan:craftableCountOf(self._item:name())
    else
        error("Unknown craft request")
    end
end

---@private
function ItemSlot:increaseQuality()
    self:setItem(self._item:increaseQuality())
    self:qualityOverlay():refresh()
    self:countOverlay():refresh()
    self._tooltip:refresh()
end

---@private
function ItemSlot:decreaseQuality()
    self:setItem(self._item:decreaseQuality())
    self:qualityOverlay():refresh()
    self:countOverlay():refresh()
    self._tooltip:refresh()
end

---@private
---@return LuaItemPrototype
function ItemSlot:itemPrototype()
    return ItemFluidPrototypes.instance():findItemFluidPrototype(self._item:name())
end

---@private
---@param message LocalisedString
function ItemSlot:presentSuccess(message)
    self:luaPlayer().play_sound { path = "utility/inventory_click" }
    if message then
        self:luaPlayer().create_local_flying_text { text = message, create_at_cursor = true }
    end
end

---@private
---@param message LocalisedString
function ItemSlot:presentFailure(message)
    self:luaPlayer().play_sound { path = "utility/cannot_build" }
    if message then
        self:luaPlayer().create_local_flying_text { text = message, create_at_cursor = true }
    end
end

---@private
function ItemSlot:searchFactory()
    remote.call("factory-search", "search", self:luaPlayer(), self._item:nameQualityPair())
end

function ItemSlot:onHover()
    self._tooltip:onHover()
end

function ItemSlot:onLeave()
    self._tooltip:onLeave()
end

---@public
---@return boolean
function ItemSlot:tooltipsAreVisible()
    return self:button():hasTooltips()
end

---@public
---@param tooltip LocalisedString
function ItemSlot:showTooltips(tooltip)
    self:button():showTooltips(tooltip)
end

---@public
function ItemSlot:hideTooltips()
    self:button():hideTooltips()
end

---@public
---@return Item
function ItemSlot:item()
    return self:thing()
end

function ItemSlot:thing()
    return self._item
end

---@private
---@return DimOverlay
function ItemSlot:dimOverlay()
    return self:child(DimOverlay)
end

---@private
---@return CountOverlay
function ItemSlot:countOverlay()
    return self:child(CountOverlay)
end

---@private
---@return QualityOverlay
function ItemSlot:qualityOverlay()
    return self:child(QualityOverlay)
end

---@private
---@return ItemButton
function ItemSlot:button()
    return self:child(ItemButton)
end
