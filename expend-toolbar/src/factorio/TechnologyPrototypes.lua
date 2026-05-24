import("core.Cache")

---@class TechnologyPrototypes : Object
---@field private __instance TechnologyPrototypes
---@field private _technologyPrototypeByUnlockedRecipe Cache
TechnologyPrototypes = Object:extendAs("factorio.TechnologyPrototypes")

function TechnologyPrototypes.new()
    local this = TechnologyPrototypes:super(Object.new())
    this._technologyPrototypeByUnlockedRecipe = Cache.new(function(unlockedRecipeName)
        return this:freshFirstTechnologyPrototypeByUnlockedRecipe(unlockedRecipeName)
    end)
    return this
end

---@public
---@return TechnologyPrototypes
function TechnologyPrototypes.instance()
    return TechnologyPrototypes.__instance
end
TechnologyPrototypes.__instance = TechnologyPrototypes.new()

---@public
---@param unlockedRecipeName string
---@return LuaTechnologyPrototype
function TechnologyPrototypes:findFirstTechnologyPrototypeUnlockingRecipe(unlockedRecipeName)
    return self._technologyPrototypeByUnlockedRecipe:get(unlockedRecipeName)
end

---@public
---@param unlockedRecipeName string
---@return LuaRecipePrototype
function TechnologyPrototypes:freshFirstTechnologyPrototypeByUnlockedRecipe(unlockedRecipeName)
    local prototypes = prototypes.get_technology_filtered({
        {
            mode = "and",
            filter = "unlocks-recipe",
            recipe = unlockedRecipeName
        }
    })

    for name, technologyPrototype in pairs(prototypes) do
        return technologyPrototype
    end
    return nil
end
