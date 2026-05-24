import("model.Item")
import("core.Memento")
import("factorio.ItemFluidPrototypes")
import("factorio.RichText")

---@class CraftingProduct : Object
---@field private _name string
---@field private _prototype LuaItemPrototype | LuaFluidPrototype
---@field private _recipeAmount number
---@field private _craftableCount number
---@field private _craftableCountText string
---@field private _recipeAmountText string
CraftingProduct = Object:extendAs("player.inventory.personal.character.crafting.CraftingProduct")

---@public
---@param product Product
---@param recipeCraftableCount number
---@param inventory Inventory
---@return CraftingProduct
function CraftingProduct.new(product, recipeCraftableCount, inventory)
    local this = CraftingProduct:super(Object.new())
    this._name = product.name
    this._prototype = ItemFluidPrototypes.instance():findItemFluidPrototype(this._name)
    this._recipeAmount = product.amount and product.probability * product.amount or product.probability * (product.amount_max + product.amount_min)
    this._craftableCount = recipeCraftableCount * this._recipeAmount
    this._inventoryCount = inventory:content():count(Item.new(this._name))

    this._craftableCountText = Memento.new(function() return this:freshCraftableCountText() end)
    this._inventoryCountText = Memento.new(function() return this:freshInventoryCountText() end)
    this._recipeAmountText = Memento.new(function() return this:freshRecipeAmountText() end)
    return this
end

---@public
---@return number
function CraftingProduct:recipeAmount()
    return self._recipeAmount
end

---@public
---@return number
function CraftingProduct:craftableCount()
    return self._craftableCount
end

---@public
---@return LocalisedText
function CraftingProduct:fullDescription(craftableCountWidth, inventoryCountWidth, recipeAmountWidth)
    local description = LocalisedText.new()
    if self._craftableCount > 0 then
        description:append(RichText.colorWhiteStart())
    else
        description:append(RichText.colorRedStart())
    end
    description:append(RichText.icon("item", self._name))
               :append(RichText.fontMonospacedStart())
               :append(RichText.leftPad(craftableCountWidth, self:craftableCountText()))
               :append(RichText.leftPad(inventoryCountWidth, self:inventoryCountText()))
               :append(RichText.leftPad(recipeAmountWidth, self:recipeAmountText()))
               :append(RichText.fontEnd())
               :append(" ")
               :append(self._prototype.localised_name)
               :append(RichText.colorEnd())
    return description
end

---@public
---@return string
function CraftingProduct:craftableCountText()
    return self._craftableCountText:value()
end

---@private
---@return string
function CraftingProduct:freshCraftableCountText()
    return string.format(" (%s) ", RichText.count(self._craftableCount))
end

---@public
---@return string
function CraftingProduct:inventoryCountText()
    return self._inventoryCountText:value()
end

---@private
---@return string
function CraftingProduct:freshInventoryCountText()
    return string.format("[%s] ", RichText.count(self._inventoryCount))
end

---@public
---@return string
function CraftingProduct:recipeAmountText()
    return self._recipeAmountText:value()
end

---@private
---@return string
function CraftingProduct:freshRecipeAmountText()
    return string.format("%sx", RichText.count(self._recipeAmount))
end
