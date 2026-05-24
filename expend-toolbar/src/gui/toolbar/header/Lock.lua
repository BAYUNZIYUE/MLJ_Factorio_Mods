import("gui.toolbar.header.ToolbarHeaderButton")
import("gui.toolbar.header.Unlock")

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
