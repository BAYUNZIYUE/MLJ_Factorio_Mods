---@class GuiEvent
---@field _data EventData
---@field _elementIndex string
GuiEvent = Object:extendAs("gui.GuiEvent")

---@param data EventData
function GuiEvent.new(data)
    local this = GuiEvent:super(Object.new())
    this._data = data
    this._elementIndex = data.element.index
    return this
end

---@public
---@return string
function GuiEvent:isForModElement()
    return self._data.element.get_mod() == Toolbars.name
end

---@public
---@return string
function GuiEvent:elementIndex()
    return self._elementIndex
end

---@public
---@return number
function GuiEvent:tick()
    return self._data.tick
end

---@protected
---@return EventData
function GuiEvent:data()
    return self._data
end
