import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class DeleteSection : SectionHeaderButton
DeleteSection = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.Delete")

function DeleteSection.create(parent)
    return SectionHeaderButton.create(
            DeleteSection,
            parent,
            {
                type = "sprite-button",
                sprite = "utility/trash",
                style = "toolbar_content_sections_section_header_delete"
            }
    )
end

function DeleteSection.new(parent, element)
    return DeleteSection:super(SectionHeaderButton.new(parent, element))
end

function DeleteSection:onClick(click)
    if click:isLeft() then
        self:header():askForDeletion()
    end
end

function DeleteSection:lock()
    self:hide()
end

function DeleteSection:unlock()
    self:show()
end
