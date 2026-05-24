import("gui.toolbar.header.ToolbarHeaderButton")

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
