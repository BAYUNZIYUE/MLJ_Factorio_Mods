import("gui.StackedContainer")
import("gui.toolbar.Toolbar")

---@class Gui : StackedContainer
---@field private _descendantsByElementIndex table<LuaGuiElement, Component>
Gui = StackedContainer:extendAs("gui.Gui")

---@public
---@param player Player
function Gui.new(player)
    local this = Gui:super(StackedContainer.new(nil, player:luaPlayer().gui.screen, { Toolbar }))
    this:setPlayer(player)
    this._descendantsByElementIndex = {}
    return this
end

---@public
function Gui:load()
    local descendants = { self }
    while #descendants > 0 do
        ---@type Component
        local parent = table.remove(descendants)
        parent:loadChildren()
        for _, child in ipairs(parent:children()) do
            table.insert(descendants, child)
        end
    end
    self:propagateInitialization()
    self:fireSizeChange()
end

---@public
function Gui:createToolbar()
    return Toolbar.create(self):centerOnScreen()
end

---@public
function Gui:clear()
    for _, toolbar in ipairs(self:toolbars()) do
        toolbar:delete()
    end
end

---@public
function Gui:hide()
    for _, toolbar in ipairs(self:toolbars()) do
        toolbar:hide()
    end
end

---@public
function Gui:show()
    for _, toolbar in ipairs(self:toolbars()) do
        toolbar:show()
    end
end

---@private
---@param element LuaGuiElement
---@return boolean
function Gui:isRepresentedBy(element)
    return element.gui.screen == element
end

---@private
---@return Toolbar[]
function Gui:toolbars()
    return self:children()
end

---@public
---@param descendant Component
function Gui:addDescendant(descendant)
    self._descendantsByElementIndex[descendant:element().index] = descendant
end

---@public
---@param descendant Component
function Gui:removeDescendant(descendant)
    self._descendantsByElementIndex[descendant:element().index] = nil
end

---@public
---@param click Click
function Gui:handleClick(click)
    local component = self._descendantsByElementIndex[click:elementIndex()]
    if component then
        component:propagateOnClick(click)
    end
end

---@public
---@param elementChanged ElementChanged
function Gui:handleElementChanged(elementChanged)
    local component = self._descendantsByElementIndex[elementChanged:elementIndex()]
    if component then
        component:propagateOnElementChanged()
    end
end

---@public
---@param elementLocationChanged ElementLocationChanged
function Gui:handleElementLocationChanged(elementLocationChanged)
    local component = self._descendantsByElementIndex[elementLocationChanged:elementIndex()]
    if component then
        component:propagateOnElementLocationChanged()
    end
end

---@public
---@param hovered Hovered
function Gui:handleHover(hovered)
    local component = self._descendantsByElementIndex[hovered:elementIndex()]
    if component then
        component:propagateOnHover()
    end
end

---@public
---@param left Left
function Gui:handleLeave(left)
    local component = self._descendantsByElementIndex[left:elementIndex()]
    if component then
        component:propagateOnLeave()
    end
end

function Gui:propagateOnClick(click) end
function Gui:propagateOnElementChanged() end
function Gui:propagateOnElementLocationChanged() end
function Gui:propagateOnHover() end
function Gui:propagateOnLeave() end
