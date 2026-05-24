import("factorio.LocalisedText")
import("factorio.RichText")
import("factorio.TechnologyPrototypes")
import("player.inventory.personal.character.crafting.CraftingIngredient")
import("player.inventory.personal.character.crafting.CraftingProduct")

---@class CraftingPlan : Object
---@field private __texts table<string, table>
---@field private _craftingInventory CharacterMainInventory
---@field private _mainProductName string
---@field private _recipe LuaRecipe
---@field private _manuallyCraftable boolean
---@field private _researched boolean
---@field private _executable boolean
---@field private _recipeCraftableCount number
---@field private _technology LuaTechnologyPrototype
---@field private _craftingProducts Map
---@field private _craftingIngredients List
CraftingPlan = Object:extendAs("player.inventory.personal.character.crafting.CraftingPlan")

---@public
---@param mainProductName string
---@param recipe LuaRecipe
---@param characterMainInventory CharacterMainInventory
---@return CraftingPlan
function CraftingPlan.new(mainProductName, recipe, characterMainInventory)
    local this = CraftingPlan:super(Object.new())
    this._craftingInventory = characterMainInventory
    this._mainProductName = mainProductName
    this._recipe = recipe
    this._manuallyCraftable = this._craftingInventory:canCraft(recipe)
    this._researched = recipe.enabled
    this._executable = this._manuallyCraftable and this._researched
    this._recipeCraftableCount = this._craftingInventory:recipeCraftableCount(this._recipe.name)
    this._technology = TechnologyPrototypes.instance():findFirstTechnologyPrototypeUnlockingRecipe(recipe.name)

    this._craftingProducts = this:freshProducts()
    this._craftingIngredients = this:freshIngredients()
    return this
end

---@private
---@return Map<string, CraftingProduct>
function CraftingPlan:freshProducts()
    ---@param product Product
    return List.new(Product, self._recipe.products)
               :collect(Map.new("", CraftingProduct),
                        function(container, product)
                            container:set(product.name,
                                          CraftingProduct.new(product,
                                                              self._recipeCraftableCount,
                                                              self._craftingInventory))
                        end)
end

---@private
---@return List<CraftingIngredient>
function CraftingPlan:freshIngredients()
    return List
            .new(Ingredient, self._recipe.ingredients)
            :map(
            function(ingredient)
                return CraftingIngredient.new(ingredient.name, ingredient.amount, self._craftingInventory)
            end)
end

---@public
---@return boolean
function CraftingPlan:isManuallyCraftable()
    return self._manuallyCraftable
end

---@public
---@return boolean
function CraftingPlan:isResearched()
    return self._researched
end

---@public
---@param other CraftingPlan
---@return boolean
function CraftingPlan:compareTo(other)
    if self._manuallyCraftable ~= other._manuallyCraftable then
        return self._manuallyCraftable
    elseif self._researched ~= other._researched then
        return self._researched
    else
        return self:craftableCountOf(self._mainProductName) > other:craftableCountOf(self._mainProductName)
    end
end

---@public
---@param requestedCraftCount number
---@return number started crafting count
function CraftingPlan:execute(requestedCraftCount)
    if self:craftableCountOf(self._mainProductName) > 0 then
        ---@type CraftingProduct
        local craftingProduct = self._craftingProducts:get(self._mainProductName)
        return self._craftingInventory:craft(
                self._recipe,
                math.ceil(requestedCraftCount / craftingProduct:recipeAmount()))
                * craftingProduct:recipeAmount()
    else
        return 0
    end
end

---@public
---@return number
function CraftingPlan:craftableCountOf(productName)
    return self._craftingProducts:get(productName):craftableCount()
end

---@public
---@return LocalisedText
function CraftingPlan:fullDescription()
    return LocalisedText.new()
                        :concat(self:createRecipeHeader())
                        :concat(self:createTechnology())
                        :concat(self:createProducts())
                        :concat(self:createIngredients())
end

---@public
---@return LocalisedText
function CraftingPlan:compactDescription()
end

---@private
---@return LocalisedText
function CraftingPlan:createRecipeHeader()
    local description = LocalisedText.new()

    description:concat(CraftingPlan.__texts.recipeTitle)

    if self._executable then
        description:append(RichText.colorWhiteStart())
    else
        description:append(RichText.colorRedStart())
    end

    description:append(RichText.icon("recipe", self._recipe.name))
               :append(RichText.monospace())

    if not self._manuallyCraftable then
        description:concat(CraftingPlan.__texts.icons.notManuallyCraftable)
    end
    if not self._researched then
        description:concat(CraftingPlan.__texts.icons.notResearched)
    end

    if self._executable then
        description:append(RichText.fontMonospaced(string.format("(%s) ", RichText.count(self._recipeCraftableCount))))
    else
        description:append(RichText.fontMonospaced(" "))
    end

    description:append(self._recipe.localised_name)
               :append(RichText.colorEnd())

    return description
end

---@private
---@return LocalisedText
function CraftingPlan:createTechnology()
    local description = LocalisedText.new()

    if self._technology then
        description:appendNewLine()
        if self._researched then
            description:append(RichText.colorWhiteStart())
        else
            description:append(RichText.colorRedStart())
        end
        description
                :append("(")
                :append(RichText.fontSmallStart())
                :append(RichText.icon("technology", self._technology.name))
                :append(" ")
                :append(self._technology.localised_name)
                :append(RichText.fontEnd())
                :append(")")
                :append(RichText.colorEnd())
    end

    return description
end

---@private
---@return LocalisedText
function CraftingPlan:createProducts()
    local description = LocalisedText.new()
    description:concat(CraftingPlan.__texts.productsTitle)

    ---@param name string
    ---@param craftingProduct CraftingProduct
    local widths = self._craftingProducts:collect(
            {
                maxCraftableCountWidth = 0,
                maxInventoryCountWidth = 0,
                maxRecipeAmountWidth = 0,
            },
            function(container, name, craftingProduct)
                container.maxCraftableCountWidth = math.max(container.maxCraftableCountWidth,
                                                            craftingProduct:craftableCountText():len())
                container.maxInventoryCountWidth = math.max(container.maxInventoryCountWidth,
                                                            craftingProduct:inventoryCountText():len())
                container.maxRecipeAmountWidth = math.max(container.maxRecipeAmountWidth,
                                                          craftingProduct:recipeAmountText():len())
            end)

    ---@param name string
    ---@param craftingProduct CraftingProduct
    self._craftingProducts:forEach(
            function(name, craftingProduct)
                description
                        :appendNewLine()
                        :concat(craftingProduct:fullDescription(widths.maxCraftableCountWidth,
                                                                widths.maxInventoryCountWidth,
                                                                widths.maxRecipeAmountWidth))
            end)

    return description
end

---@private
---@return LocalisedText
function CraftingPlan:createIngredients()
    local description = LocalisedText.new()
    description:concat(CraftingPlan.__texts.ingredientsTitle)

    ---@param craftingIngredient CraftingIngredient
    local widths = self._craftingIngredients:collect(
            {
                maxCraftableCountWidth = 0,
                maxInventoryCountWidth = 0,
                maxRecipeAmountWidth = 0
            },
            function(container, craftingIngredient)
                container.maxCraftableCountWidth = math.max(container.maxCraftableCountWidth,
                                                            craftingIngredient:craftableCountText():len())
                container.maxInventoryCountWidth = math.max(container.maxInventoryCountWidth,
                                                            craftingIngredient:inventoryCountText():len())
                container.maxRecipeAmountWidth = math.max(container.maxRecipeAmountWidth,
                                                          craftingIngredient:recipeAmountText():len())
            end)

    ---@param craftingIngredient CraftingIngredient
    self._craftingIngredients
        :forEach(
            function(craftingIngredient)
                description
                        :appendNewLine()
                        :concat(craftingIngredient:fullDescription(widths.maxCraftableCountWidth,
                                                                   widths.maxInventoryCountWidth,
                                                                   widths.maxRecipeAmountWidth))
            end)

    return description
end

CraftingPlan.__texts = {
    monospace = LocalisedText.new():append(RichText.monospace()),

    recipeTitle = LocalisedText.new()
                               :appendNewLine()
                               :append(RichText.labelStart())
                               :append({ "description.recipe" })
                               :append(":")
                               :append(RichText.labelEnd())
                               :appendNewLine(),
    technologyTitle = LocalisedText.new()
                                   :appendNewLine()
                                   :append(RichText.labelStart())
                                   :append({ "gui-map-generator.technology-difficulty-group-tile" })
                                   :append(":")
                                   :append(RichText.labelEnd())
                                   :appendNewLine(),
    productsTitle = LocalisedText.new()
                                 :appendNewLine()
                                 :append(RichText.labelStart())
                                 :append({ "description.products" })
                                 :append(":")
                                 :append(RichText.labelEnd()),
    ingredientsTitle = LocalisedText.new()
                                    :appendNewLine()
                                    :append(RichText.labelStart())
                                    :append({ "description.ingredients" })
                                    :append(":")
                                    :append(RichText.labelEnd()),

    icons = {
        notManuallyCraftable = LocalisedText.new():append(RichText.icon("img", Toolbars.icons.notManuallyCraftable)),
        notResearched = LocalisedText.new():append(RichText.icon("img", Toolbars.icons.technologyRed)),
    },
}
