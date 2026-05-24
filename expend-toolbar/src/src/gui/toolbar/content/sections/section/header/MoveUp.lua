import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class MoveUp : SectionHeaderButton
MoveUp = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.MoveUp")

function MoveUp.create(parent)
    return SectionHeaderButton.create(
            MoveUp,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.moveSectionUp,
                style = "toolbar_content_sections_section_header_moveUp"
            }
    )
end

function MoveUp.new(parent, element)
    return MoveUp:super(SectionHeaderButton.new(parent, element))
end

function MoveUp:onClick(click)
    if click:isLeft() then
        self:section():moveUp()
    end
end

function MoveUp:lock()
    self:hide()
end

function MoveUp:unlock()
    self:show()
end
