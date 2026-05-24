---@class Content : Object
---@field private __EMPTY_TABLE table
---@field private __EMPTY Content
---@field private _content table<string, table<string, number>>
Content = Object:extendAs("player.Content")

---@public
function Content.new()
    local this = Content:super(Object.new())
    this._content = {}
    return this
end

--todo Implement as a new type to prevent modifications of it
---@public
---@return Content
function Content.empty()
    return Content.__EMPTY
end
Content.__EMPTY = Content.new()

---@public
---@param other Content
---@return self
function Content:merge(other)
    for otherName, otherQualities in pairs(other._content) do
        for otherQualityName, otherQualityCount in pairs(otherQualities) do
            local itemQualities = self._content[otherName]
            if itemQualities then
                local qualityCount = itemQualities[otherQualityName]
                if qualityCount then
                    itemQualities[otherQualityName] = qualityCount + otherQualityCount
                else
                    itemQualities[otherQualityName] = otherQualityCount
                end
            else
                self._content[otherName] = { [otherQualityName] = otherQualityCount }
            end
        end
    end

    return self
end

---@public
---@param itemsWithQualityCounts ItemWithQualityCounts[]
---@return self
function Content:addAll(itemsWithQualityCounts)
    for _, itemWithQualityCounts in ipairs(itemsWithQualityCounts) do
        self:add(itemWithQualityCounts)
    end
    return self
end

---@public
---@param itemWithQualityCounts ItemWithQualityCounts
---@return self
function Content:add(itemWithQualityCounts)
    local name = itemWithQualityCounts.name
    local quality = itemWithQualityCounts.quality
    local qualityName = (not quality
            and "normal"
            or type(quality) == "string"
            and itemWithQualityCounts.quality
            or itemWithQualityCounts.quality.name
            or "normal")

    local itemQualities = self._content[name]
    if itemQualities then
        local qualityCount = itemQualities[qualityName]
        if qualityCount then
            itemQualities[qualityName] = qualityCount + itemWithQualityCounts.count
        else
            itemQualities[qualityName] = itemWithQualityCounts.count
        end
    else
        self._content[name] = { [qualityName] = itemWithQualityCounts.count }
    end

    return self
end

---@public
---@param itemName string
---@return boolean
function Content:hasItem(itemName)
    return self._content[itemName] ~= nil
end

---@public
---@param name string
---@return table<string, number>
function Content:allQualitiesCount(name)
    local allQualitiesCount = self._content[name]
    if allQualitiesCount then
        return allQualitiesCount
    else
        return Content.__EMPTY_TABLE
    end
end
Content.__EMPTY_TABLE = {}

---@public
---@param item Item
---@return number
function Content:count(item)
    local itemQualitiesCount = self._content[item:name()]
    if itemQualitiesCount then
        local itemQualityCount = itemQualitiesCount[item:quality()]
        if itemQualityCount then
            return itemQualityCount
        else
            return 0
        end
    else
        return 0
    end
end

---@public
---@param other Content
---@return Content
function Content:changedIn(other)
    local change = Content.new()

    for itemName, itemQualityCount in pairs(self._content) do
        local otherItemQualities = other._content[itemName]
        if otherItemQualities then
            for quality, count in pairs(itemQualityCount) do
                local otherItemQualityCount = otherItemQualities[quality]
                if otherItemQualityCount then
                    if count ~= otherItemQualityCount then
                        change:add({ name = itemName, quality = quality, count = otherItemQualityCount })
                    end
                else
                    change:add({ name = itemName, quality = quality, count = 0 })
                end
            end
        else
            for quality, _ in pairs(itemQualityCount) do
                change:add({ name = itemName, quality = quality, count = 0 })
            end
        end
    end

    for otherItemName, otherItemQualityCount in pairs(other._content) do
        local itemQualities = self._content[otherItemName]
        if itemQualities then
            for quality, count in pairs(otherItemQualityCount) do
                if not itemQualities[quality] then
                    change:add({ name = otherItemName, quality = quality, count = count })
                end
            end
        else
            for quality, count in pairs(otherItemQualityCount) do
                change:add({ name = otherItemName, quality = quality, count = count })
            end
        end
    end

    return change
end

---@public
---@return table<string, table<string, number>>
function Content:map()
    return self._content
end

---@public
---@return boolean
function Content:isEmpty()
    for _, _ in pairs(self._content) do
        return false
    end
    return true
end

---@public
---@param other Content
---@return boolean
function Content:equals(other)
    return self:contains(other) and other:contains(self)
end

---@private
---@param other Content
---@return boolean
function Content:contains(other)
    local this = self._content
    for name, qualities in pairs(other._content) do
        if this[name] == nil then
            return false
        else
            for key, value in pairs(qualities) do
                if this[name][key] == nil then
                    return false
                else
                    if this[name][key] ~= value then
                        return false
                    end
                end
            end
        end
    end
    return true
end
