import("Cache")

---@class RecipePrototypes : Object
---@field private __instance RecipePrototypes
---@field private _recipePrototypesNamesByItemProductName Cache
RecipePrototypes = Object:extendAs("factorio.RecipePrototypes")

function RecipePrototypes.new()
    local this = RecipePrototypes:super(Object.new())
    this._recipePrototypesNamesByItemProductName = Cache.new(function(itemProductName)
        return this:freshRecipePrototypesNamesByItemProductName(itemProductName)
    end)
    return this
end

---@public
---@return RecipePrototypes
function RecipePrototypes.instance()
    return RecipePrototypes.__instance
end
RecipePrototypes.__instance = RecipePrototypes.new()

---@public
---@param itemProductName string
---@return string[]
function RecipePrototypes:findRecipePrototypesNamesByItemProductName(itemProductName)
    return self._recipePrototypesNamesByItemProductName:get(itemProductName)
end

---@private
---@param itemProductName string
---@return string[]
function RecipePrototypes:freshRecipePrototypesNamesByItemProductName(itemProductName)
    local prototypes = prototypes.get_recipe_filtered(
            {
                {
                    mode = "and",
                    invert = true,
                    filter = "hidden",
                },
                {
                    mode = "and",
                    invert = true,
                    filter = "hidden-from-player-crafting"
                },
                {
                    mode = "and",
                    filter = "has-product-item",
                    elem_filters = { { filter = "name", name = itemProductName } }
                },
            })
    local prototypesNames = {}
    for name, prototype in pairs(prototypes) do
        table.insert(prototypesNames, name)
    end
    return prototypesNames
end
