import("core.Memento")
import("factorio.RichText")
import("factorio.ItemFluidPrototypes")
import("model.Item")

---@class CraftingIngredient : Object
---@field private _name string
---@field private _prototype LuaItemPrototype | LuaFluidPrototype
---@field private _inventory Inventory
---@field private _recipeAmount number
---@field private _inventoryCount number
---@field private _craftableCountText Memento<string>
---@field private _inventoryCountText Memento<string>
---@field private _recipeAmountText Memento<string>
---@field private _bestCraftingPlan Memento<CraftingPlan>
CraftingIngredient = Object:extendAs("player.inventory.personal.character.crafting.CraftingIngredient")

---@public
---@param _inventory Inventory
---@param name string
---@return CraftingIngredient
function CraftingIngredient.new(name, recipeAmount, _inventory)
    local this = CraftingIngredient:super(Object.new())
    this._name = name
    this._prototype = ItemFluidPrototypes.instance():findItemFluidPrototype(name)
    this._recipeAmount = recipeAmount
    this._inventory = _inventory

    this._craftableCountText = Memento.new(function() return this:freshCraftableCountText() end)
    this._inventoryCountText = Memento.new(function() return this:freshInventoryCountText() end)
    this._recipeAmountText = Memento.new(function() return this:freshRecipeAmountText() end)

    this._bestCraftingPlan = Memento.new(function() return this:freshBestCraftingPlan() end)
    return this
end

---@public
---@param craftableCountWidth number
---@param inventoryCountWidth number
---@param recipeAmountWidth number
---@return LocalisedText
function CraftingIngredient:fullDescription(craftableCountWidth, inventoryCountWidth, recipeAmountWidth)
    local craftingPlan = self:bestCraftingPlan()
    local craftableCount = craftingPlan and craftingPlan:craftableCountOf(self._name) or 0
    local inventoryCount = self._inventory:content():count(Item.new(self._name))

    local isLacking = inventoryCount + craftableCount < self._recipeAmount
    local needsIngredientsCrafting = inventoryCount < self._recipeAmount and inventoryCount + craftableCount > self._recipeAmount

    local description = LocalisedText.new()
    if isLacking then
        description:append(RichText.colorRedStart())
    elseif needsIngredientsCrafting then
        description:append(RichText.colorLightOrangeStart())
    else
        description:append(RichText.colorWhiteStart())
    end

    description
            :append(RichText.icon(self._prototype.type, self._name))
            :append(RichText.fontMonospacedStart())
            :append(" ")
            :append(RichText.leftPad(craftableCountWidth, self:craftableCountText()))
            :append(RichText.leftPad(inventoryCountWidth, self:inventoryCountText()))
            :append("/")
            :append(RichText.leftPad(recipeAmountWidth, self:recipeAmountText()))
            :append(RichText.fontEnd())
            :append(" ")
            :append(self._prototype.localised_name)
            :append(RichText.colorEnd())

    return description
end

---@public
---@return string
function CraftingIngredient:craftableCountText()
    return self._craftableCountText:value()
end

---@private
---@return string
function CraftingIngredient:freshCraftableCountText()
    local craftingPlan = self:bestCraftingPlan()
    if not craftingPlan then
        return ""
    elseif not craftingPlan:isManuallyCraftable() then
        return ""
    elseif not craftingPlan:isResearched() then
        return "(T) "
    else
        return string.format("(%s) ", RichText.count(craftingPlan:craftableCountOf(self._name)))
    end
end

---@public
---@return string
function CraftingIngredient:inventoryCountText()
    return self._inventoryCountText:value()
end

---@private
---@return string
function CraftingIngredient:freshInventoryCountText()
    return RichText.count(self._inventory:content():count(Item.new(self._name)))
end

---@public
---@return string
function CraftingIngredient:recipeAmountText()
    return self._recipeAmountText:value()
end

---@public
---@return string
function CraftingIngredient:freshRecipeAmountText()
    return RichText.count(self._recipeAmount) .. "x"
end

---@private
---@return CraftingPlan
function CraftingIngredient:bestCraftingPlan()
    return self._bestCraftingPlan:value()
end

function CraftingIngredient:freshBestCraftingPlan()
    local craftingPlans = self._inventory:craftingPlansInDescendingCountOrderForAnItem(self._name)
    if next(craftingPlans) then
        return craftingPlans[1]
    else
        return nil
    end
end
