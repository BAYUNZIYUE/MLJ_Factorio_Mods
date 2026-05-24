import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class ConfirmDeleteSection : SectionHeaderButton
ConfirmDeleteSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.ConfirmDelete")

function ConfirmDeleteSection.create(parent)
    return SectionHeaderButton.create(
            ConfirmDeleteSection,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.confirm,
                style = "toolbar_content_sections_section_header_confirmDelete"
            }
    )
end

function ConfirmDeleteSection.new(parent, element)
    return ConfirmDeleteSection:super(SectionHeaderButton.new(parent, element))
end

function ConfirmDeleteSection:onClick(click)
    if click:isLeft() then
        self:section():delete()
    end
end
