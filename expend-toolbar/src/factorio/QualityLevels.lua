import("core.Cache")

---@class QualityPrototypes : Object
---@field private __instance QualityPrototypes
---@field private _qualityLevels Cache
QualityLevels = Object:extendAs("factorio.QualityPrototypes")

function QualityLevels.new()
    local this = QualityLevels:super(Object.new())
    this._qualityLevels = Cache.new(function(name)
        local quality = prototypes.quality[name]
        return quality and quality.level or 0
    end)
    return this
end

---@public
---@return QualityPrototypes
function QualityLevels.instance()
    return QualityLevels.__instance
end
QualityLevels.__instance = QualityLevels.new()

---@public
---@param name string
---@return number
function QualityLevels:getQualityLevel(name)
    return self._qualityLevels:get(name)
end
