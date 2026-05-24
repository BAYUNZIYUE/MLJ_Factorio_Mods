---@class SlotHistory : Object
---@field private _lastPickedSlot Slot
SlotHistory = Object:extendAs("gui.toolbar.content.sections.section.content.table.SlotHistory")

---@param player_index number
function SlotHistory:getInstanceFor(player_index)
    if SlotHistory.__perPlayer == nil then
        SlotHistory.__perPlayer = {}
    end
    if not SlotHistory.__perPlayer[player_index] then
        SlotHistory.__perPlayer[player_index] = SlotHistory.new()
    end
    return SlotHistory.__perPlayer[player_index]
end

---@private
---@return SlotHistory
function SlotHistory.new()
    local this = SlotHistory:super(Object.new())
    this._lastPickedSlot = nil
    return this
end

---@public
---@return boolean
function SlotHistory:hasLastPickedSlot()
    return self._lastPickedSlot ~= nil and self._lastPickedSlot:isValid()
end

---@public
---@return Slot
function SlotHistory:lastPickedSlot()
    return self._lastPickedSlot
end

---@public
---@param slot Slot
function SlotHistory:rememberPick(slot)
    self._lastPickedSlot = slot
end

---@public
function SlotHistory:forgetPick()
    self._lastPickedSlot = nil
end
