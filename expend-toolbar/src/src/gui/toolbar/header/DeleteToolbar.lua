import("gui.toolbar.header.ToolbarHeaderButton")

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
