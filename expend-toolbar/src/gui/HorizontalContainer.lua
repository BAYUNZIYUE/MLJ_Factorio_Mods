import("gui.Container")

---@class HorizontalContainer : Container
HorizontalContainer = Container:extendAs("gui.HorizontalContainer")

function HorizontalContainer.create(class, parent, addParameters, builder)
    addParameters.direction = "horizontal"
    return Container.create(class, parent, addParameters, builder)
end

function HorizontalContainer.new(parent, root, childrenClasses)
    return HorizontalContainer:super(Container.new(parent, root, childrenClasses))
end

function HorizontalContainer:freshWidth()
    local width = 0
    for _, child in ipairs(self:children()) do
        width = width + child:width()
    end
    return width + self:box():totalWidthSpacing() + self:extraSpacing()
end

function HorizontalContainer:freshDisplayWidth()
    if not self:isVisible() then
        return 0
    end

    local displayWidth = 0
    for _, child in ipairs(self:children()) do
        displayWidth = displayWidth + child:displayWidth()
    end
    return displayWidth + self:box():scale(self:display():scaleValue()):totalWidthSpacing() + self:display():scale(self:extraSpacing())
end

function HorizontalContainer:freshHeight()
    local biggestChildHeight = 0
    for _, child in ipairs(self:children()) do
        if child:height() > biggestChildHeight then
            biggestChildHeight = child:height()
        end
    end
    return biggestChildHeight + self:box():totalHeightSpacing()
end

function HorizontalContainer:freshDisplayHeight()
    if not self:isVisible() then
        return 0
    end

    local biggestChildDisplayHeight = 0
    for _, child in ipairs(self:children()) do
        if child:displayHeight() > biggestChildDisplayHeight then
            biggestChildDisplayHeight = child:displayHeight()
        end
    end
    return biggestChildDisplayHeight + self:box():scale(self:display():scaleValue()):totalHeightSpacing()
end

---@protected
---@return number
function HorizontalContainer:extraSpacing()
    return 0
end
