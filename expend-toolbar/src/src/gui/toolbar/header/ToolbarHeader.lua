import("gui.HorizontalContainer")
import("gui.toolbar.Toolbar")
import("gui.toolbar.header.AlignBottom")
import("gui.toolbar.header.AlignTop")
import("gui.toolbar.header.CancelDeleteToolbar")
import("gui.toolbar.header.CollapseToolbar")
import("gui.toolbar.header.ConfirmDeleteToolbar")
import("gui.toolbar.header.DeleteToolbar")
import("gui.toolbar.header.ExpandToolbar")
import("gui.toolbar.header.Lock")
import("gui.toolbar.header.OneSectionMode")
import("gui.toolbar.header.ToolbarDrag")
import("gui.toolbar.header.Unlock")

---@class ToolbarHeader : HorizontalContainer
ToolbarHeader = HorizontalContainer:extendAs("gui.toolbar.header.Header")

function ToolbarHeader.create(parent)
    return HorizontalContainer.create(
            ToolbarHeader,
            parent,
            {
                type = "flow",
                style = "toolbar_header"
            },
            function(instance)
                Lock.create(instance)
                AlignBottom.create(instance)
                ToolbarDrag.create(instance)
                OneSectionMode.create(instance)
                CollapseToolbar.create(instance)
                DeleteToolbar.create(instance)
            end
    )
end

function ToolbarHeader.new(parent, root)
    return ToolbarHeader:super(HorizontalContainer.new(
            parent,
            root,
            { Lock, Unlock,
              AlignBottom, AlignTop,
              ToolbarDrag,
              OneSectionMode,
              CollapseToolbar, ExpandToolbar,
              DeleteToolbar, CancelDeleteToolbar, ConfirmDeleteToolbar
            }))
end

function ToolbarHeader:initilize()
    self:migrateTo_2_12_0()
    self:migrateTo_2_19_0()
end

---@private
function ToolbarHeader:migrateTo_2_12_0()
    if not (self:child(AlignBottom) or self:child(AlignTop)) then
        AlignBottom.create(self, 2)
        if self:isLocked() then
            self:child(AlignBottom):lock()
        end
    end
end

---@private
function ToolbarHeader:migrateTo_2_19_0()
    if not self:child(OneSectionMode) then
        OneSectionMode.create(self, 4)
        if self:isLocked() then
            self:child(OneSectionMode):lock()
        end
    end
end

---@public
function ToolbarHeader:askForDeletion()
    self:child(DeleteToolbar):delete()
    ConfirmDeleteToolbar.create(self)
    CancelDeleteToolbar.create(self)
end

---@public
function ToolbarHeader:cancelDeletion()
    self:child(CancelDeleteToolbar):delete()
    self:child(ConfirmDeleteToolbar):delete()
    DeleteToolbar.create(self)
end

---@public
---@return boolean
function ToolbarHeader:isLocked()
    return self:child(Unlock) ~= nil
end

function ToolbarHeader:toggle()
    if self:isVisible() then
        self:hide()
    else
        self:show()
    end
end

function ToolbarHeader:freshWidth()
    return 0
end

function ToolbarHeader:freshDisplayWidth()
    return 0
end
