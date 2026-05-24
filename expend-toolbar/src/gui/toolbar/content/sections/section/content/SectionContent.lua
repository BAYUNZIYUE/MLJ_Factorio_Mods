import("gui.VerticalContainer")
import("gui.toolbar.content.sections.section.content.table.Table")

---@class SectionContent : VerticalContainer
SectionContent = VerticalContainer:extendAs("gui.toolbar.content.sections.section.content.Content")

function SectionContent.create(parent)
    return VerticalContainer.create(
            SectionContent,
            parent,
            {
                type = "flow",
                style = "toolbar_content_sections_section_content"
            },
            function(instance)
                Table.create(instance)
            end
    )
end

function SectionContent.new(parent, element)
    return SectionContent:super(VerticalContainer.new(parent, element, { Table }))
end

---@public
---@return Table
function SectionContent:table()
    return self:child(Table)
end
