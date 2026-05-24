import("gui.toolbar.header.ToolbarHeaderButton")

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
