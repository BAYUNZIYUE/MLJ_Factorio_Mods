import("gui.VerticalContainer")

---@class Window : VerticalContainer
Window = VerticalContainer:extendAs("gui.Window")

function Window.create(class, parent, style, builder)
    return VerticalContainer.create(
            class,
            parent,
            {
                type = "frame",
                style = style
            },
            builder
    )
end

function Window.new(parent, element, childrenClasses)
    return Window:super(VerticalContainer.new(parent, element, childrenClasses))
end

function Window:onElementLocationChanged(_)
    self:keepWithinTheScreen()
    self:turnOffCenteringOnScreen()
end

---@private
function Window:keepWithinTheScreen()
    if self:displayWidth() > self:display():resolution():width() then
        self:dockToRight()
    else
        if self:isDockedToLeft() then
            self:dockToLeft()
        elseif self:isDockedToRight() then
            self:dockToRight()
        end
    end

    if self:displayHeight() > self:display():resolution():height() then
        if self:isAlignedTop() then
            self:dockToTop()
        else
            self:dockToBottom()
        end
    else
        if self:isDockedToTop() then
            self:dockToTop()
        elseif self:isDockedToBottom() then
            self:dockToBottom()
        end
    end
end

---@private
---@param x number
function Window:setX(x)
    local location = self:location()
    location.x = x
    self:setLocation(location)
end

---@private
---@param y number
function Window:setY(y)
    local location = self:location()
    location.y = y
    self:setLocation(location)
end

---@private
---@param location GuiLocation
function Window:setLocation(location)
    location.x = math.floor(location.x)
    location.y = math.floor(location.y)
    self:element().location = location
end

---@private
function Window:turnOffCenteringOnScreen()
    self:element().auto_center = false
end

---@public
function Window:centerOnScreen()
    self:element().force_auto_center()
end

function Window:onWidthChange()
    local isDockedToLeft = self:isDockedToLeft()
    local isDockedToRight = self:isDockedToRight()

    Window:super().onWidthChange(self)

    if self:displayWidth() > self:display():resolution():width() then
        self:dockToRight()
    else
        if isDockedToLeft then
            self:dockToLeft()
        elseif isDockedToRight then
            self:dockToRight()
        end
    end
end

function Window:onHeightChange()
    local isDockedToTop = self:isDockedToTop()
    local isDockedToBottom = self:isDockedToBottom()

    local previousY = self:location().y
    local previousDisplayHeight = self:displayHeight()

    Window:super().onHeightChange(self)

    if self:displayHeight() > self:display():resolution():height() then
        if self:isAlignedTop() then
            self:dockToTop()
        else
            self:dockToBottom()
        end
    else
        if self:isAlignedTop() then
            if isDockedToTop then
                self:dockToTop()
            elseif isDockedToBottom then
                self:dockToBottom()
            end
        else
            self:setY(previousY + (previousDisplayHeight - self:displayHeight()))
            if isDockedToBottom then
                self:dockToBottom()
            elseif isDockedToTop then
                self:dockToTop()
            end
        end
    end
end

---@public
---@return boolean
function Window:isAlignedTop()
    return true
end

---@private
---@return boolean
function Window:isDockedToLeft()
    return self:location().x <= 0
end

---@private
function Window:dockToLeft()
    self:setX(0)
end

---@private
---@return boolean
function Window:isDockedToTop()
    return self:location().y <= 0
end

---@private
function Window:dockToTop()
    self:setY(0)
end

---@private
---@return boolean
function Window:isDockedToRight()
    return self:location().x + self:displayWidth() >= self:resolution():width()
end

---@private
function Window:dockToRight()
    self:setX(self:resolution():width() - self:displayWidth())
end

---@private
---@return boolean
function Window:isDockedToBottom()
    return self:location().y + self:displayHeight() >= self:resolution():height()
end

---@private
function Window:dockToBottom()
    self:setY(self:resolution():height() - self:displayHeight())
end

---@private
---@return GuiLocation
function Window:location()
    return self:element().location
end
