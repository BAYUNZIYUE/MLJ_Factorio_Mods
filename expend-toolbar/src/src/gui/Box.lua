---@class Box
---@field private __none Box
---
---@field private _leftBorder number
---@field private _leftMargin number
---@field private _leftPadding number
---@field private _width number
---@field private _rightPadding number
---@field private _rightMargin number
---@field private _rightBorder number
---
---@field private _topBorder number
---@field private _topMargin number
---@field private _topPadding number
---@field private _height number
---@field private _bottomPadding number
---@field private _bottomMargin number
---@field private _bottomBorder number
Box = Object:extendAs("gui.Box")

function Box.new()
    local this = Box:super(Object.new())

    this._leftBorder = 0
    this._leftMargin = 0
    this._leftPadding = 0
    this._width = 0
    this._rightPadding = 0
    this._rightMargin = 0
    this._rightBorder = 0

    this._topBorder = 0
    this._topMargin = 0
    this._topPadding = 0
    this._height = 0
    this._bottomPadding = 0
    this._bottomMargin = 0
    this._bottomBorder = 0

    return this
end

---@public
---@return Box
function Box.none()
    return Box.__none
end
Box.__none = Box.new()

---@public
---@param border number
---@return self
function Box:withBorder(border)
    return self
            :withLeftBorder(border):withRightBorder(border)
            :withTopBorder(border):withBottomBorder(border)
end

---@public
---@param size number
---@return self
function Box:withContentSize(size)
    return self:withWidth(size):withHeight(size)
end

---@public
---@return number
function Box:totalWidth()
    return self._width + self:totalWidthSpacing();
end

function Box:width()
    return self._width
end

---@public
---@return number
function Box:totalWidthSpacing()
    return self._leftBorder +
            self._leftMargin +
            self._leftPadding +
            self._rightPadding +
            self._rightMargin +
            self._rightBorder;
end

---@public
---@param leftBorder number
---@return self
function Box:withLeftBorder(leftBorder)
    self._leftBorder = leftBorder
    return self
end

---@public
---@param leftMargin number
---@return self
function Box:withLeftMargin(leftMargin)
    self._leftMargin = leftMargin
    return self
end

---@public
---@param leftPadding number
---@return self
function Box:withLeftPadding(leftPadding)
    self._leftPadding = leftPadding
    return self
end

---@public
---@param width number
---@return self
function Box:withWidth(width)
    self._width = width
    return self
end

---@public
---@param rightPadding number
---@return self
function Box:withRightPadding(rightPadding)
    self._rightPadding = rightPadding
    return self
end

---@public
---@param rightMargin number
---@return self
function Box:withRightMargin(rightMargin)
    self._rightMargin = rightMargin
    return self
end

---@public
---@param rightBorder number
---@return self
function Box:withRightBorder(rightBorder)
    self._rightBorder = rightBorder
    return self
end

-- HEIGHT

---@public
---@return number
function Box:totalHeight()
    return self._height + self:totalHeightSpacing()
end

---@public
---@return number
function Box:totalHeightSpacing()
    return self._topBorder +
            self._topMargin +
            self._topPadding +
            self._bottomPadding +
            self._bottomMargin +
            self._bottomBorder
end

---@public
---@param topBorder number
---@return self
function Box:withTopBorder(topBorder)
    self._topBorder = topBorder
    return self
end

---@public
---@param topMargin number
---@return self
function Box:withTopMargin(topMargin)
    self._topMargin = topMargin
    return self
end

---@public
---@param topMargin number
---@return self
function Box:withTopMargin(topMargin)
    self._topMargin = topMargin
    return self
end

---@public
---@param topPadding number
---@return self
function Box:withTopPadding(topPadding)
    self._topPadding = topPadding
    return self
end

---@public
---@param height number
---@return self
function Box:withHeight(height)
    self._height = height
    return self
end

---@public
---@param bottomPadding number
---@return self
function Box:withBottomPadding(bottomPadding)
    self._bottomPadding = bottomPadding
    return self
end

---@public
---@param bottomMargin number
---@return self
function Box:withBottomMargin(bottomMargin)
    self._bottomMargin = bottomMargin
    return self
end

---@public
---@param bottomBorder number
---@return self
function Box:withBottomBorder(bottomBorder)
    self._bottomBorder = bottomBorder
    return self
end

---@public
---@param scale number
---@return Box
function Box:scale(scale)
    if self == Box.__none then
        return self
    end
    local scaled = Box.new()
    scaled._leftBorder = self:scaleSize(self._leftBorder, scale)
    scaled._leftMargin = self:scaleSize(self._leftMargin, scale)
    scaled._leftPadding = self:scaleSize(self._leftPadding, scale)
    scaled._width = self:scaleSize(self._width, scale)
    scaled._rightPadding = self:scaleSize(self._rightPadding, scale)
    scaled._rightMargin = self:scaleSize(self._rightMargin, scale)
    scaled._rightBorder = self:scaleSize(self._rightBorder, scale)

    scaled._topBorder = self:scaleSize(self._topBorder, scale)
    scaled._topMargin = self:scaleSize(self._topMargin, scale)
    scaled._topPadding = self:scaleSize(self._topPadding, scale)
    scaled._height = self:scaleSize(self._height, scale)
    scaled._bottomPadding = self:scaleSize(self._bottomPadding, scale)
    scaled._bottomMargin = self:scaleSize(self._bottomMargin, scale)
    scaled._bottomBorder = self:scaleSize(self._bottomBorder, scale)
    return scaled
end

---@private
---@param size number
---@param scale number
function Box:scaleSize(size, scale)
    return math.floor(size * scale)
end
