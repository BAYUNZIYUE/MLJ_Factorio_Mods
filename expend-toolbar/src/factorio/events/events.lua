import("core.Event")
import("gui.GuiEvent")

-- 这些类只承担 EventBus topic 和少量事件数据包装，集中放在一起比一类一文件更容易扫读。

---@class Clear : Event
Clear = Event:extendAs("factorio.events.controls.Clear")

---@class DecreaseQuality : Event
DecreaseQuality = Event:extendAs("factorio.events.controls.DecreaseQuality")

---@class IncreaseQuality : Event
IncreaseQuality = Event:extendAs("factorio.events.controls.IncreaseQuality")

---@class OpenFactoriopedia : Event
OpenFactoriopedia = Event:extendAs("factorio.events.controls.OpenFactoriopedia")

---@class Pick : Event
Pick = Event:extendAs("factorio.events.controls.Pick")

---@class SearchFactory : Event
SearchFactory = Event:extendAs("factorio.events.controls.SearchFactory")

---@class ToggleToolbarHeader : Event
ToggleToolbarHeader = Event:extendAs("factorio.events.controls.ToggleToolbarHeader")

---@class ControllerChanged : Event
ControllerChanged = Event:extendAs("factorio.events.general.ControllerChanged")

---@class SurfaceChanged : Event
SurfaceChanged = Event:extendAs("factorio.events.general.SurfaceChanged")

---@class Tick : Event
Tick = Event:extendAs("factorio.events.general.Tick")

---@param tick number
function Tick.new(tick)
    return Tick:super(Event.new(tick))
end

---@class PlayerMainInventoryChanged : Event
PlayerMainInventoryChanged = Event:extendAs("factorio.events.inventory.PlayerMainInventoryChanged")

---@class PlayerTrashInventoryChanged : Event
PlayerTrashInventoryChanged = Event:extendAs("factorio.events.inventory.PlayerTrashInventoryChanged")

---@class PlayerSettingChanged : Event
PlayerSettingChanged = Event:extendAs("factorio.events.settings.PlayerSettingChanged")

function PlayerSettingChanged.new(settingName)
    return PlayerSettingChanged:super(Event.new(settingName))
end

---@class SpidertronDeleted : Event
---@field private _unitNumber number
SpidertronDeleted = Event:extendAs("factorio.events.entities.SpidertronDeleted")

---@public
---@param unitNumber number
---@return SpidertronDeleted
function SpidertronDeleted.new(unitNumber)
    local instance = SpidertronDeleted:super(Event.new(unitNumber))
    instance._unitNumber = unitNumber
    return instance
end

---@public
---@return number
function SpidertronDeleted:unitNumber()
    return self._unitNumber
end

---@class ChangedEvent : GuiEvent
ChangedEvent = GuiEvent:extendAs("factorio.events.gui.ChangedEvent")

---@param eventData EventData
function ChangedEvent.new(eventData)
    return ChangedEvent:super(GuiEvent.new(eventData))
end

---@class ElementChanged : ChangedEvent
ElementChanged = ChangedEvent:extendAs("factorio.events.gui.ElementChanged")

---@param eventData EventData
function ElementChanged.new(eventData)
    return ElementChanged:super(ChangedEvent.new(eventData))
end

---@class ElementLocationChanged : ChangedEvent
ElementLocationChanged = ChangedEvent:extendAs("factorio.events.gui.ElementLocationChanged")

---@param eventData EventData
function ElementLocationChanged.new(eventData)
    return ElementLocationChanged:super(ChangedEvent.new(eventData))
end

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

---@class Hovered : GuiEvent
Hovered = GuiEvent:extendAs("factorio.events.gui.Hovered")

---@param eventData EventData
function Hovered.new(eventData)
    return Hovered:super(GuiEvent.new(eventData))
end

---@class Left : GuiEvent
Left = GuiEvent:extendAs("factorio.events.gui.Left")

---@param eventData EventData
function Left.new(eventData)
    return Left:super(GuiEvent.new(eventData))
end
