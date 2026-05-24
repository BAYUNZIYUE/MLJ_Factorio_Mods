import("gui.Leaf")
import("gui.Box")
import("gui.toolbar.Toolbar")
import("gui.toolbar.header.ToolbarHeader")

---@class ToolbarHeaderButton : Leaf
---@field private _header ToolbarHeader
---@field private _toolbar Toolbar
ToolbarHeaderButton = Leaf:extendAs("gui.toolbar.header.Button")

function ToolbarHeaderButton.new(parent, root)
    return ToolbarHeaderButton:super(Leaf.new(parent, root))
end

function ToolbarHeaderButton:initilize()
    self._header = self:ancestor(ToolbarHeader)
    self._toolbar = self:ancestor(Toolbar)
end

function ToolbarHeaderButton:lock()
    self:element().style.size = 16
    self:fireSizeChange()
end

function ToolbarHeaderButton:unlock()
    self:element().style.size = 20
    self:fireSizeChange()
end

function ToolbarHeaderButton:box()
    if self:isLocked() then
        return Box.new():withContentSize(16)
    else
        return Box.new():withContentSize(20)
    end
end

---@protected
---@return boolean
function ToolbarHeaderButton:isLocked()
    return self:element().style.maximal_width == 16
end

---@protected
---@return ToolbarHeader
function ToolbarHeaderButton:header()
    return self._header
end

---@protected
---@return Toolbar
function ToolbarHeaderButton:toolbar()
    return self._toolbar
end
