import("core.Cache")

---@class ItemFluidPrototypes : Object
---@field private __instance ItemFluidPrototypes
---@field private _itemFluidPrototypes Cache
ItemFluidPrototypes = Object:extendAs("factorio.ItemFluidPrototypes")

function ItemFluidPrototypes.new()
    local this = ItemFluidPrototypes:super(Object.new())
    this._itemFluidPrototypes = Cache.new(function(name)
        return prototypes.item[name] or prototypes.fluid[name]
    end)
    return this
end

---@public
---@return ItemFluidPrototypes
function ItemFluidPrototypes.instance()
    return ItemFluidPrototypes.__instance
end
ItemFluidPrototypes.__instance = ItemFluidPrototypes.new()

---@public
---@param name string
---@return LuaItemPrototype | LuaFluidPrototype
function ItemFluidPrototypes:findItemFluidPrototype(name)
    return self._itemFluidPrototypes:get(name)
end
