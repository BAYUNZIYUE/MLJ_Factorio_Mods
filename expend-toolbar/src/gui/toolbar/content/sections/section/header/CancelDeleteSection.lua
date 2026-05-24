import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class CancelDeleteSection : SectionHeaderButton
CancelDeleteSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.CancelDelete")

function CancelDeleteSection.create(parent)
    return SectionHeaderButton.create(
            CancelDeleteSection,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.cancel,
                style = "toolbar_content_sections_section_header_cancelDelete"
            }
    )
end

function CancelDeleteSection.new(parent, element)
    return CancelDeleteSection:super(SectionHeaderButton.new(parent, element))
end

function CancelDeleteSection:onClick(click)
    if click:isLeft() then
        self:header():cancelDeletion()
    end
end
