import("gui.Leaf")
import("gui.Box")
import("gui.toolbar.Toolbar")

---@class AddSection : Leaf
---@field private _toolbar Toolbar
AddSection = Leaf:extendAs("gui.toolbar.content.AddSection")

function AddSection.create(parent)
    return Leaf.create(
            AddSection,
            parent,
            {
                type = "button",
                sprite = Toolbars.icons.expand,
                style = "toolbar_content_addSection"
            },
            function(instance)
                instance:element().caption = "Add section"
            end
    )
end

function AddSection.new(parent, element)
    return AddSection:super(Leaf.new(parent, element))
end

function AddSection:initilize()
    self:setBox(Toolbars.styles.toolbar.content.addSection.box)
    self._toolbar = self:ancestor(Toolbar)
end

function AddSection:onClick(click)
    if click:isLeft() then
        self._toolbar:addSection()
    end
end

function AddSection:lock()
    self:hide()
end

function AddSection:unlock()
    self:show()
end
