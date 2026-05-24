import("gui.Container")

---@class VerticalContainer : Container
VerticalContainer = Container:extendAs("gui.VerticalContainer")

function VerticalContainer.create(class, parent, addParameters, builder)
    addParameters.direction = "vertical"
    return Container.create(class, parent, addParameters, builder)
end

function VerticalContainer.new(parent, element, childrenClasses)
    return VerticalContainer:super(Container.new(parent, element, childrenClasses))
end

function VerticalContainer:freshWidth()
    local biggestChildWidth = 0
    for _, child in ipairs(self:children()) do
        if child:width() > biggestChildWidth then
            biggestChildWidth = child:width()
        end
    end
    return biggestChildWidth + self:box():totalWidthSpacing()
end

function VerticalContainer:freshDisplayWidth()
    if not self:isVisible() then
        return 0
    end

    local biggestChildDisplayWidth = 0
    for _, child in ipairs(self:children()) do
        if child:displayWidth() > biggestChildDisplayWidth then
            biggestChildDisplayWidth = child:displayWidth()
        end
    end
    return biggestChildDisplayWidth + self:box():scale(self:display():scaleValue()):totalWidthSpacing()
end

function VerticalContainer:freshHeight()
    local height = 0
    for _, child in ipairs(self:children()) do
        height = height + child:height()
    end
    return height + self:box():totalHeightSpacing() + self:extraSpacing()
end

function VerticalContainer:freshDisplayHeight()
    if not self:isVisible() then
        return 0
    end

    local displayHeight = 0
    for _, child in ipairs(self:children()) do
        displayHeight = displayHeight + child:displayHeight()
    end
    return displayHeight + self:box():scale(self:display():scaleValue()):totalHeightSpacing() + self:display():scale(self:extraSpacing())
end

function VerticalContainer:extraSpacing()
    return 0
end
