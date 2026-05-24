import("gui.toolbar.content.sections.section.header.SectionHeaderButton")

---@class MoveDown : SectionHeaderButton
MoveDown = SectionHeaderButton:extendAs("gui.toolbar.content.sections.section.header.MoveDown")

function MoveDown.create(parent)
    return SectionHeaderButton.create(
            MoveDown,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.moveSectionDown,
                style = "toolbar_content_sections_section_header_moveDown"
            }
    )
end

function MoveDown.new(parent, element)
    return MoveDown:super(SectionHeaderButton.new(parent, element))
end

function MoveDown:onClick(click)
    if click:isLeft() then
        self:section():moveDown()
    end
end

function MoveDown:lock()
    self:hide()
end

function MoveDown:unlock()
    self:show()
end
