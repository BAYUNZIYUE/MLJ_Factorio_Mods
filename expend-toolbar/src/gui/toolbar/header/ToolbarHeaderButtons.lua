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

---@class AlignBottom : ToolbarHeaderButton
---@field private _toolbar Toolbar
AlignBottom = ToolbarHeaderButton:extendAs("gui.toolbar.header.AlignBottom")

function AlignBottom.create(parent, index)
    return ToolbarHeaderButton.create(
            AlignBottom,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.alignToolbarBottom,
                style = "toolbar_header_align_bottom",
                index = index
            }
    )
end

function AlignBottom.new(parent, root)
    return AlignBottom:super(ToolbarHeaderButton.new(parent, root))
end

function AlignBottom:initilize()
    AlignBottom:super().initilize(self)
    self._toolbar = self:ancestor(Toolbar)
end

function AlignBottom:onClick(click)
    if click:isLeft() then
        self._toolbar:alignBottom()
        local alignTop = AlignTop.create(self:parent())
        if self:isLocked() then
            alignTop:lock()
        end
        self:replaceWith(alignTop)
    end
end

function AlignBottom:lock()
    self:hide()
end

function AlignBottom:unlock()
    self:show()
end

---@class AlignTop : ToolbarHeaderButton
---@field private _toolbar Toolbar
AlignTop = ToolbarHeaderButton:extendAs("gui.toolbar.header.AlignTop")

function AlignTop.create(parent)
    return ToolbarHeaderButton.create(
            AlignTop,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.alignToolbarTop,
                style = "toolbar_header_align_top"
            }
    )
end

function AlignTop.new(parent, root)
    return AlignTop:super(ToolbarHeaderButton.new(parent, root))
end

function AlignTop:initilize()
    AlignTop:super().initilize(self)
    self._toolbar = self:ancestor(Toolbar)
end

function AlignTop:onClick(click)
    if click:isLeft() then
        self._toolbar:alignTop()
        local alignBottom = AlignBottom.create(self:parent())
        if self:isLocked() then
            alignBottom:lock()
        end
        self:replaceWith(alignBottom)
    end
end

function AlignTop:lock()
    self:hide()
end

function AlignTop:unlock()
    self:show()
end

---@class CancelDeleteToolbar : ToolbarHeaderButton
CancelDeleteToolbar = ToolbarHeaderButton:extendAs("gui.toolbar.header.CancelDelete")

function CancelDeleteToolbar.create(parent)
    return ToolbarHeaderButton.create(
            CancelDeleteToolbar,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.cancel,
                style = "toolbar_header_cancelDelete"
            }
    )
end

function CancelDeleteToolbar.new(parent, root)
    return CancelDeleteToolbar:super(ToolbarHeaderButton.new(parent, root))
end

function CancelDeleteToolbar:onClick(click)
    if click:isLeft() then
        self:header():cancelDeletion()
    end
end

---@class CollapseToolbar : ToolbarHeaderButton
CollapseToolbar = ToolbarHeaderButton:extendAs("gui.toolbar.header.Collapse")

function CollapseToolbar.create(parent)
    return ToolbarHeaderButton.create(
            CollapseToolbar,
            parent,
            {
                type = "sprite-button",
                style = "toolbar_header_collapse"
            }
    )
end

function CollapseToolbar.new(parent, root)
    return CollapseToolbar:super(ToolbarHeaderButton.new(parent, root))
end

function CollapseToolbar:initilize()
    CollapseToolbar:super().initilize(self)
    if self:toolbar():isAlignedTop() then
        self:alignTop()
    else
        self:alignBottom()
    end
end

function CollapseToolbar:onClick(click)
    if click:isLeft() then
        self:toolbar():collapse()
    end
end

---@public
function CollapseToolbar:collapsed()
    local expand = ExpandToolbar.create(self:parent())
    if self:isLocked() then
        expand:lock()
    end
    self:replaceWith(expand)
end

function CollapseToolbar:alignTop()
    self:element().sprite = Toolbars.icons.collapseUpward
end

function CollapseToolbar:alignBottom()
    self:element().sprite = Toolbars.icons.collapseDownward
end

---@class ConfirmDeleteToolbar : ToolbarHeaderButton
ConfirmDeleteToolbar = ToolbarHeaderButton:extendAs("gui.toolbar.header.ConfirmDelete")

function ConfirmDeleteToolbar.create(parent)
    return ToolbarHeaderButton.create(
            ConfirmDeleteToolbar,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.confirm,
                style = "toolbar_header_confirmDelete"
            }
    )
end

function ConfirmDeleteToolbar.new(parent, root)
    return ConfirmDeleteToolbar:super(ToolbarHeaderButton.new(parent, root))
end

function ConfirmDeleteToolbar:onClick(click)
    if click:isLeft() then
        self:toolbar():delete()
    end
end

---@class DeleteToolbar : ToolbarHeaderButton
DeleteToolbar = ToolbarHeaderButton:extendAs("gui.toolbar.header.Delete")

function DeleteToolbar.create(parent)
    return ToolbarHeaderButton.create(
            DeleteToolbar,
            parent,
            {
                type = "sprite-button",
                sprite = "utility/trash",
                style = "toolbar_header_delete"
            }
    )
end

function DeleteToolbar.new(parent, root)
    return DeleteToolbar:super(ToolbarHeaderButton.new(parent, root))
end

function DeleteToolbar:onClick(click)
    if click:isLeft() then
        self:header():askForDeletion()
    end
end

function DeleteToolbar:lock()
    self:hide()
end

function DeleteToolbar:unlock()
    self:show()
end

---@class ExpandToolbar : ToolbarHeaderButton
ExpandToolbar = ToolbarHeaderButton:extendAs("gui.toolbar.header.Expand")

function ExpandToolbar.create(parent)
    return ToolbarHeaderButton.create(
            ExpandToolbar,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.expand,
                style = "toolbar_header_expand"
            }
    )
end

function ExpandToolbar.new(parent, root)
    return ExpandToolbar:super(ToolbarHeaderButton.new(parent, root))
end

function ExpandToolbar:initilize()
    ExpandToolbar:super().initilize(self)
    self:migrateTo_2_16_0()
end

function ExpandToolbar:migrateTo_2_16_0()
    self:element().sprite = Toolbars.icons.expand
end

function ExpandToolbar:onClick(click)
    if click:isLeft() then
        self:toolbar():expand()
    end
end

---@public
function ExpandToolbar:expanded()
    local collapse = CollapseToolbar.create(self:parent())
    if self:isLocked() then
        collapse:lock()
    end
    self:replaceWith(collapse)
end

---@class Lock : ToolbarHeaderButton
Lock = ToolbarHeaderButton:extendAs("gui.toolbar.header.Lock")

function Lock.create(parent)
    return ToolbarHeaderButton.create(
            Lock,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.padlockOpen,
                style = "toolbar_header_lock"
            }
    )
end

function Lock.new(parent, root)
    return Lock:super(ToolbarHeaderButton.new(parent, root))
end

function Lock:onClick(click)
    if click:isLeft() then
        self:toolbar():lock()
    end
end

function Lock:lock()
    self:replaceWith(Unlock.create(self:parent()))
end

---@class ToolbarDrag : Leaf
ToolbarDrag = Leaf:extendAs("gui.toolbar.header.ToolbarDrag")

function ToolbarDrag.create(parent)
    return Leaf.create(
            ToolbarDrag,
            parent,
            {
                type = "empty-widget",
                style = "toolbar_drag"
            },
            function(instance)
                instance:element().drag_target = instance:ancestor(Toolbar):element()
            end
    )
end

function ToolbarDrag.new(parent, root)
    return ToolbarDrag:super(Leaf.new(parent, root))
end

function ToolbarDrag:onDoubleLeftClick()
    self:luaPlayer().play_sound { path = "utility/gui_click" }
    self:ancestor(Toolbar):toggle()
end

---@class Unlock : ToolbarHeaderButton
Unlock = ToolbarHeaderButton:extendAs("gui.toolbar.header.Unlock")

function Unlock.create(parent)
    return Component.create(
            Unlock,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.padlockClosed,
                style = "toolbar_header_unlock"
            },
            function(instance)
                instance:lock()
            end
    )
end

function Unlock.new(parent, root)
    return Unlock:super(ToolbarHeaderButton.new(parent, root))
end

function Unlock:onClick(click)
    if click:isLeft() then
        self:toolbar():unlock()
    end
end

function Unlock:unlock()
    self:replaceWith(Lock.create(self:parent()))
end
