import("gui.toolbar.Toolbar")
import("gui.toolbar.header.ToolbarHeaderButton")
import("gui.toolbar.header.AlignTop")

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
