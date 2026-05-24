import("gui.toolbar.header.ToolbarHeaderButton")

---@class OneSectionMode : ToolbarHeaderButton
OneSectionMode = ToolbarHeaderButton:extendAs("gui.toolbar.header.OneSectionMode")

function OneSectionMode.create(parent, index)
    return ToolbarHeaderButton.create(
            OneSectionMode,
            parent,
            {
                type = "sprite-button",
                sprite = Toolbars.icons.one,
                style = "toolbar_header_one_section_mode",
                auto_toggle = true,
                index = index
            }
    )
end

function OneSectionMode.new(parent, root)
    return OneSectionMode:super(ToolbarHeaderButton.new(parent, root))
end

function OneSectionMode:onClick(click)
    if click:isLeft() and self:toggled() then
        self:toolbar():collapseAllSections()
    end
end

---@public
---@return boolean
function OneSectionMode:toggled()
    return self:element().toggled
end

function OneSectionMode:lock()
    self:hide()
end

function OneSectionMode:unlock()
    self:show()
end
