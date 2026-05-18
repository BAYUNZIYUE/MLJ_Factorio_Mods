local Public = {}

function Public.from_quality(quality)
    if quality == nil then
        return 1
    end
    return (quality.level or 0) + 1
end

return Public
