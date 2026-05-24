import("Cache")
import("factorio.RecipePrototypes")

---@class Recipes : Object
---@field private _luaPlayer LuaPlayer
---@field private _recipesByItemProductName Cache
Recipes = Object:extendAs("Recipes")

---@param luaPlayer LuaPlayer
function Recipes.new(luaPlayer)
    local this = Recipes:super(Object.new())
    this._luaPlayer = luaPlayer
    this._recipesByItemProductName = Cache.new(function(itemProductName)
        return this:freshRecipesByItemProductName(itemProductName)
    end)

    return this
end

---@public
---@param itemProductName string
---@return LuaRecipe[]
function Recipes:findRecipesByItemProductName(itemProductName)
    return self._recipesByItemProductName:get(itemProductName)
end

---@private
---@param itemProductName string
---@return LuaRecipe[]
function Recipes:freshRecipesByItemProductName(itemProductName)
    local recipes = {}

    local recipePrototypesNames = RecipePrototypes.instance()
                                                  :findRecipePrototypesNamesByItemProductName(itemProductName)
    for i, recipePrototypeName in ipairs(recipePrototypesNames) do
        local recipe = self._luaPlayer.force.recipes[recipePrototypeName]
        if recipe then
            table.insert(recipes, recipe)
        end
    end

    return recipes
end
