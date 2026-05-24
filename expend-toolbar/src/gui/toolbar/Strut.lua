import("gui.Leaf")

---@class Strut : Leaf
---@field private _width number
Strut = Leaf:extendAs("gui.toolbar.Strut")

---@public
---@param parent Component
---@return Strut
function Strut.create(parent)
    return Leaf.create(Strut, parent, { type = "empty-widget" })
end

function Strut.new(parent, root)
    return Strut:super(Leaf.new(parent, root))
end

function Strut:initilize()
    self._width = self:element().style.minimal_width or 0
    self:setBox(Box.new():withWidth(self._width))
end

---@public
---@param width number
function Strut:setWidth(width)
    self:element().style.minimal_width = width
    self._width = width
    self:setBox(Box.new():withWidth(width))
    self:onWidthChange()
end
