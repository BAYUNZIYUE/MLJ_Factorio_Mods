import("gui.Container")

---@class StackedContainer : Container
StackedContainer = Container:extendAs("gui.StackedContainer")

function StackedContainer.new(parent, root, childrenClasses)
    return StackedContainer:super(Container.new(parent, root, childrenClasses))
end

function StackedContainer:freshWidth()
    local biggestChildWidth = 0
    for _, child in ipairs(self:children()) do
        if child:width() > biggestChildWidth then
            biggestChildWidth = child:width()
        end
    end
    return biggestChildWidth + self:box():totalWidthSpacing()
end

function StackedContainer:freshDisplayWidth()
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

function StackedContainer:freshHeight()
    local biggestChildHeight = 0
    for _, child in ipairs(self:children()) do
        if child:height() > biggestChildHeight then
            biggestChildHeight = child:height()
        end
    end
    return biggestChildHeight + self:box():totalHeightSpacing()
end

function StackedContainer:freshDisplayHeight()
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
