import("gui.HorizontalContainer")
import("gui.toolbar.Toolbar")
import("gui.toolbar.header.ToolbarHeaderButtons")

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
              CollapseToolbar, ExpandToolbar,
              DeleteToolbar, CancelDeleteToolbar, ConfirmDeleteToolbar
            }))
end

function ToolbarHeader:initilize()
    self:migrateTo_2_12_0()
    self:migrateToTabMode()
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
function ToolbarHeader:migrateToTabMode()
    for _, child in ipairs(self:element().children) do
        if child.tags and child.tags.className == "gui.toolbar.header.OneSectionMode" then
            child.destroy()
            break
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
