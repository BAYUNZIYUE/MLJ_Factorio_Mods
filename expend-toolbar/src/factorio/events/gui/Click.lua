import("gui.GuiEvent")

---@class Click : GuiEvent
Click = GuiEvent:extendAs("factorio.events.gui.Click")

---@param eventData EventData
function Click.new(eventData)
    return Click:super(GuiEvent.new(eventData))
end

---@public
---@return boolean
function Click:isLeft()
    return self:data().button == defines.mouse_button_type.left
end

---@public
---@return boolean
function Click:isMiddle()
    return self:data().button == defines.mouse_button_type.middle
end

---@public
---@return boolean
function Click:isRight()
    return self:data().button == defines.mouse_button_type.right
end

---@public
---@return boolean
function Click:isButton5()
    return self:data().button == 32
end

---@public
---@return boolean
function Click:withModifier()
    return self:withCtrl() or self:withAlt() or self:withShift()
end

---@public
---@return boolean
function Click:withOnlyCtrl()
    return self:withCtrl() and not self:withAlt() and not self:withShift()
end

---@public
---@return boolean
function Click:withCtrl()
    return self:data().control
end

---@public
---@return boolean
function Click:withOnlyAlt()
    return self:withAlt() and not self:withCtrl() and not self:withShift()
end

---@public
---@return boolean
function Click:withAlt()
    return self:data().alt
end

---@public
---@return boolean
function Click:withOnlyShift()
    return self:withShift() and not self:withCtrl() and not self:withAlt()
end

---@public
---@return boolean
function Click:withShift()
    return self:data().shift
end
