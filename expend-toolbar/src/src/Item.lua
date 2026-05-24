import("Thing")

---@class Item : Thing
Item = Thing:extendAs("Item")

---@public
---@param name string
---@param quality string optional
function Item.new(name, quality)
    local this = Item:super(Thing.new(name))
    this._quality = quality and quality or "normal"
    return this
end

function Item:id()
    return self:name() .. "_" .. self:quality()
end

---@public
---@return string
function Item:quality()
    return self._quality
end

---@public
---@return Item
function Item:increaseQuality()
    local quality = prototypes.quality[self:quality()]
    if not quality then
        return self
    end

    local next = quality.next
    if next then
        return Item.new(self:name(), next.name)
    else
        return self
    end
end

---@public
---@return Item
function Item:decreaseQuality()
    if not prototypes.quality[self:quality()] then
        return self
    end

    local previous
    for _, quality in pairs(prototypes.quality) do
        if quality.next and quality.next.name == self:quality() then
            previous = quality
        end
    end
    if previous then
        return Item.new(self:name(), previous.name)
    else
        return self
    end
end

---@public
---@return ItemIDAndQualityIDPair
function Item:nameQualityPair()
    return { name = self:name(), quality = self:quality() }
end
