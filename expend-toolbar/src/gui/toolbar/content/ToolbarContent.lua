import("gui.VerticalContainer")
import("gui.toolbar.Toolbar")
import("gui.toolbar.content.AddSection")
import("gui.toolbar.content.sections.Sections")

---@class ToolbarContent : VerticalContainer
ToolbarContent = VerticalContainer:extendAs("gui.toolbar.content.Content")

function ToolbarContent.create(parent)
    return VerticalContainer.create(
            ToolbarContent,
            parent,
            {
                type = "scroll-pane",
                vertical_scroll_policy = "never",
                style = "toolbar_content"
            },
            function(instance)
                Sections.create(instance)
                AddSection.create(instance)
            end
    )
end

function ToolbarContent.new(parent, element)
    return ToolbarContent:super(VerticalContainer.new(parent, element, { Sections, AddSection }))
end

function ToolbarContent:initilize()
    self:migrateTo_2_14_0()
end

function ToolbarContent:migrateTo_2_14_0()
    self:element().vertical_scroll_policy = "never"
end

function ToolbarContent:alignTop()
    if not self:isAlignedTop() then
        return self:sections():swapWith(self:addSectionButton())
    end
end

---@private
---@return boolean
function ToolbarContent:isAlignedTop()
    return not self:isAlignedBottom()
end

function ToolbarContent:alignBottom()
    if not self:isAlignedBottom() then
        return self:sections():swapWith(self:addSectionButton())
    end
end

---@private
---@return boolean
function ToolbarContent:isAlignedBottom()
    return self:sections():element().get_index_in_parent() ~= 1
end

---@public
---@return Sections
function ToolbarContent:sections()
    return self:child(Sections)
end

---@private
---@return AddSection
function ToolbarContent:addSectionButton()
    return self:child(AddSection)
end
