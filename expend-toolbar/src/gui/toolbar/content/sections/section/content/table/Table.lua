import("gui.Sized")
import("gui.Box")
import("gui.toolbar.content.sections.section.content.table.Row")
import("gui.toolbar.content.sections.section.content.table.Slot")

---@class Table : Sized
---@field private _toolbar Toolbar
Table = Sized:extendAs("gui.toolbar.content.sections.section.content.table.Table")

function Table.create(parent)
    return Sized.create(
            Table,
            parent,
            {
                type = "frame",
                direction = "vertical",
                style = "toolbar_content_sections_section_content_table"
            }
    )
end

function Table.new(parent, element)
    return Table:super(Sized.new(parent, element, { Row }))
end

function Table:initilize()
    self:setBox(Toolbars.styles.toolbar.content.sections.section.content.box)
    self._toolbar = self:ancestor(Toolbar)
end

function Table:lock()
    self:trim()
end

---@public
function Table:trim()
    self:trimRowsTo(math.max(1, self:lastOccupiedRowIndex()))
    self:trimColumnsToMinimum(self:columnsCount())
    self:fireSizeChange()
end

function Table:unlock()
    self:adjustUnlocked()
end

---@public
function Table:adjustUnlocked()
    self:ensureRowsMinimum(1)
    self:adjustUnlockedColumns()
    self:adjustUnlockedRows()
    self:fireSizeChange()
end

---@private
function Table:adjustUnlockedRows()
    self:addRowWhenTailFilled()
    self:removeIdleTailRows()
end

---@private
---@param minimum number
function Table:ensureRowsMinimum(minimum)
    if self:rowsCount() < minimum then
        local missingRows = minimum - self:rowsCount()
        local i = 0
        while i < missingRows do
            Row.create(self)
            i = i + 1
        end
    end
end

---@private
---@param lastRowToLeaveIndex number
function Table:trimRowsTo(lastRowToLeaveIndex)
    for _, row in ipairs(self:rows()) do
        if row:index() > lastRowToLeaveIndex then
            row:delete()
        end
    end
end

---@private
---@return number
function Table:lastOccupiedRowIndex()
    local lastOccupiedRowIndex = 0
    for _, row in ipairs(self:rows()) do
        if row:isOccupied() then
            lastOccupiedRowIndex = math.max(lastOccupiedRowIndex, row:index())
        end
    end
    return lastOccupiedRowIndex
end

---@private
function Table:adjustUnlockedColumns()
    self:ensureColumnsMinimum(self:columnsCount())
    self:trimColumnsToMinimum(self:columnsCount())
end

---@private
---@return number
function Table:columnsCount()
    return math.max(self._toolbar:pageColumns(), self:lastOccupiedColumnIndex())
end

---@private
---@param minimum number
function Table:ensureColumnsMinimum(minimum)
    for _, row in ipairs(self:rows()) do
        row:ensureColumnsMinimum(minimum)
    end
end

---@private
---@param minimum number
function Table:trimColumnsToMinimum(minimum)
    for _, row in ipairs(self:rows()) do
        row:trimColumnsToMinimum(minimum)
    end
end

---@private
function Table:addRowWhenTailFilled()
    -- 最后一格被占用才扩一行，避免像旧实现那样横向无限长。
    while self:rows()[self:rowsCount()]:tailHasThing() do
        local row = Row.create(self)
        row:ensureColumnsMinimum(self:columnsCount())
    end
end

---@private
function Table:removeIdleTailRows()
    -- 只有倒数第二行的末格也空着时才收尾行，保证玩家始终有一行可继续放新物品。
    while self:rowsCount() > 1 and not self:rows()[self:rowsCount()]:isOccupied()
            and not self:rows()[self:rowsCount() - 1]:tailHasThing() do
        self:rows()[self:rowsCount()]:delete()
    end
end

---@public
---@return number
function Table:lastOccupiedColumnIndex()
    local rows = self:rows()
    local lastOccupiedColumn = 0
    for _, row in ipairs(rows) do
        lastOccupiedColumn = math.max(lastOccupiedColumn, row:lastOccupiedColumnIndex())
    end
    return lastOccupiedColumn
end

---@public
---@return number
function Table:freshWidth()
    return self:columnsCount() * Slot:size()
end

---@public
---@return number
function Table:freshDisplayWidth()
    return self:columnsCount() * self:scale(Slot:size())
end

---@public
---@return number
function Table:freshHeight()
    return self:rowsCount() * Slot:size() + self:box():totalHeightSpacing()
end

---@public
---@return number
function Table:freshDisplayHeight()
    return self:rowsCount() * self:scale(Slot:size()) + self:box():scale(self:display():scaleValue()):totalHeightSpacing()
end

---@private
---@return number
function Table:rowsCount()
    return #self:rows()
end

---@private
---@return Row[]
function Table:rows()
    return self:children()
end
