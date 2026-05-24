import("gui.toolbar.Toolbar")
import("gui.toolbar.header.ToolbarHeaderButton")
import("gui.toolbar.header.AlignBottom")

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
