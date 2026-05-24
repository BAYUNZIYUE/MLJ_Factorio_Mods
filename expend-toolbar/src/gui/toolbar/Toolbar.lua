import("factorio.events.events")
import("gui.Box")
import("gui.Window")
import("gui.toolbar.Strut")
import("gui.toolbar.header.ToolbarHeader")
import("gui.toolbar.content.ToolbarContent")
import("gui.toolbar.content.sections.Sections")
import("gui.toolbar.content.sections.section.Section")
import("gui.toolbar.content.sections.section.content.table.Table")
import("player.events.ToolbarsToggled")

---@class Toolbar : Window
Toolbar = Window:extendAs("gui.toolbar.Toolbar")

function Toolbar.create(parent)
    return Window.create(
            Toolbar,
            parent,
            "toolbar",
            function(instance)
                ToolbarHeader.create(instance)
                ToolbarContent.create(instance)
                Strut.create(instance)
                instance:adjustGrids()
            end
    )
end

function Toolbar.new(parent, element)
    return Toolbar:super(Window.new(parent, element, { ToolbarHeader, ToolbarContent, Strut }))
end

function Toolbar:initilize()
    self:setBox(Toolbars.styles.toolbar.box)

    self:setControls({ [ToggleToolbarHeader] = function() self:header():toggle() end })
    self:player():eventBus():subscribeTo(ToolbarsToggled, self, function(event) self:refresh(event) end)
    self:player():eventBus():subscribeTo(PlayerSettingChanged.new(Toolbars.settings.columns), self, function()
        self:tableChanged()
    end)

    self:selectFallbackPage()
    self:freezeWidth()
end

---@public
function Toolbar:toggle()
    if self:content():isVisible() then
        self:collapse()
    else
        self:expand()
    end
end

---@public
function Toolbar:collapse()
    local collapseToolbar = self:header():child(CollapseToolbar)
    if collapseToolbar then
        collapseToolbar:collapsed()
    end
    self:content():hide()
end

---@public
function Toolbar:expand()
    local expandToolbar = self:header():child(ExpandToolbar)
    if expandToolbar then
        expandToolbar:expanded()
    end
    self:content():show()
end

---@public
function Toolbar:collapseAllSections()
    for _, section in ipairs(self:content():sections():sections()) do
        section:collapse()
    end
end

---@public
function Toolbar:addSection()
    local section
    if self:isAlignedTop() then
        section = self:content():sections():addSectionOntoEnd()
    else
        section = self:content():sections():addSectionOntoStart()
    end
    self:selectPage(section)
    self:adjustGrids()
end

---@public
---@return number
function Toolbar:sectionsCount()
    return self:content():sections():count()
end

---@public
function Toolbar:tableChanged()
    self:adjustGrids()
    self:freezeWidth()
    self:keepWithinTheScreen()
end

---@public
function Toolbar:adjustGrids()
    if not self:isLocked() then
        for _, table in ipairs(self:tables()) do
            table:adjustUnlocked()
        end
    end
end

---@public
---@param section Section
function Toolbar:selectPage(section)
    self:content():sections():select(section)
    self:adjustGrids()
    self:freezeWidth()
    self:keepWithinTheScreen()
end

---@public
function Toolbar:selectFallbackPage()
    self:content():sections():selectFallback()
end

---@public
---@return number
function Toolbar:pageColumns()
    return self:player():settings():toolbarColumns()
end

function Toolbar:lock()
    Toolbar:super().lock(self)
    self:freezeWidth()
end

function Toolbar:unlock()
    Toolbar:super().unlock(self)
    self:freezeWidth()
end

---@private
function Toolbar:freezeWidth()
    -- 旧存档可能没有 Strut；这里顺手补齐，避免锁定宽度时 nil 访问。
    if not self:strut() then
        Strut.create(self)
    end

    self:strut():setWidth(self:content():width())

    -- 旧版本曾直接写 minimal_width，当前统一交给 Strut 控制宽度。
    self:element().style.minimal_width = 0
    if self:header() then
        self:header():element().style.minimal_width = 0
    end
end

function Toolbar:extraSpacing()
    return (self:header() and self:header():isVisible() and self:content() and self:content():isVisible()) and self:scale(Toolbars.styles.toolbar.spacing) or 0
end

---@private
function Toolbar:refresh()
    if self:isOn() then
        self:show()
    else
        self:hide()
    end
end

function Toolbar:show()
    if self:isOn() then
        Toolbar:super().show(self)
    end
end

---@private
---@return boolean
function Toolbar:isOn()
    return self:player():toolbarsAreOn()
end

---@private
---@return boolean
function Toolbar:isLocked()
    return self:child(ToolbarHeader):isLocked()
end

---@public
function Toolbar:alignTop()
    if not self:isAlignedTop() then
        self:header():swapWith(self:content())
        self:keepWithinTheScreen()
        Toolbar:super().alignTop(self)
    end
end

---@public
---@return boolean
function Toolbar:isAlignedTop()
    return not self:isAlignedBottom()
end

---@public
function Toolbar:alignBottom()
    if not self:isAlignedBottom() then
        self:header():swapWith(self:content())
        self:keepWithinTheScreen()
        Toolbar:super().alignBottom(self)
    end
end

---@public
---@return boolean
function Toolbar:isAlignedBottom()
    return self:header() and self:header():element().get_index_in_parent() ~= 1
end

---@public
---@return ToolbarHeader
function Toolbar:header()
    return self:child(ToolbarHeader)
end

---@private
---@return ToolbarContent
function Toolbar:content()
    return self:child(ToolbarContent)
end

---@private
---@return Table[]
function Toolbar:tables()
    local tables = {}
    for _, section in pairs(self:content():sections():sections()) do
        table.insert(tables, section:content():table())
    end
    return tables
end

---@private
---@return Strut
function Toolbar:strut()
    return self:child(Strut)
end
