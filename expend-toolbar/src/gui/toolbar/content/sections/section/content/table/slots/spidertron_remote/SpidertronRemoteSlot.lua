import("model.SpidertronRemote")
import("factorio.events.controls.Pick")
import("factorio.events.entities.SpidertronDeleted")
import("gui.toolbar.content.sections.section.content.table.Slot")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteButton")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteCountOverlay")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteDimOverlay")
import("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemotePlanetOverlay")

---@private
---@class SpidertronRemoteSlot : Slot
---@field private _spidertronRemote SpidertronRemote
SpidertronRemoteSlot = Slot:extendAs("gui.toolbar.content.sections.section.content.table.slots.spidertron_remote.SpidertronRemoteSlot")
SpidertronRemoteSlot.__serializedSpidertronRemoteTagName = "spidertron-remote"

---@public
---@param parent Component
---@param spidertronRemote SpidertronRemote
function SpidertronRemoteSlot.create(parent, spidertronRemote)
    return Slot.create(
            SpidertronRemoteSlot,
            parent,
            function(instance)
                instance:saveSpidertronRemote(spidertronRemote)
                SpidertronRemoteButton.create(instance, { "left", "middle" })
                SpidertronRemoteDimOverlay.create(instance)
                SpidertronRemoteCountOverlay.create(instance, spidertronRemote:unitsCount())
                SpidertronRemotePlanetOverlay.create(instance, spidertronRemote:planet())
            end
    )
end

function SpidertronRemoteSlot.new(parent, root)
    return SpidertronRemoteSlot:super(Slot.new(parent, root,
                                               { SpidertronRemoteButton,
                                                 SpidertronRemoteCountOverlay,
                                                 SpidertronRemoteDimOverlay,
                                                 SpidertronRemotePlanetOverlay }))
end

function SpidertronRemoteSlot:initilize()
    SpidertronRemoteSlot:super().initilize(self)
    self:setControls({ [Pick] = function() self:pick() end })

    local loadedSpidertronRemote = self:loadSpidertronRemote()
    self._spidertronRemote = loadedSpidertronRemote:refreshed()
    self:saveSpidertronRemote(self._spidertronRemote)
    self:refresh()

    self:registerPlanetChangedHandler()
    self:registerHighlightHandlers()
    self:registerSpidertronDeleteHandlers()
end

---@private
---@param spidertronRemote SpidertronRemote
function SpidertronRemoteSlot:saveSpidertronRemote(spidertronRemote)
    self:setTag(SpidertronRemoteSlot.__serializedSpidertronRemoteTagName, spidertronRemote:serialize())
end

---@private
---@return SpidertronRemote
function SpidertronRemoteSlot:loadSpidertronRemote()
    return SpidertronRemote.deserialize(self:getTag(SpidertronRemoteSlot.__serializedSpidertronRemoteTagName))
end

---@private
function SpidertronRemoteSlot:registerPlanetChangedHandler()
    self:player():eventBus():subscribeTo(SurfaceChanged, self, function(_)
        self:refresh()
    end)
end

---@private
function SpidertronRemoteSlot:refresh()
    self:countOverlay():refresh()
    self:dimOverlay():refresh()
    self:planetOverlay():refresh()
end

---@private
function SpidertronRemoteSlot:registerHighlightHandlers()
    local eventBus = self:player():eventBus()
    eventBus:subscribeTo(Picked.new(self:thing()), self, function(_) self:button():highlight() end)
    eventBus:subscribeTo(Released.new(self:thing()), self, function(_) self:button():unhighlight() end)
end

---@private
function SpidertronRemoteSlot:unregisterHighlightHandlers()
    local eventBus = self:player():eventBus()
    eventBus:unsubscribeFrom(Picked.new(self:thing()), self)
    eventBus:unsubscribeFrom(Released.new(self:thing()), self)
end

---@private
function SpidertronRemoteSlot:registerSpidertronDeleteHandlers()
    local eventBus = self:player():eventBus()
    for i, unitNumber in ipairs(self._spidertronRemote:unitNumbers()) do
        eventBus:subscribeTo(SpidertronDeleted.new(unitNumber), self,
                             function(event) self:onSpidertronDelete(event:unitNumber()) end)
    end
end

---@private
---@param unitNumber number
function SpidertronRemoteSlot:unregisterSpidertronDeleteHandlerFor(unitNumber)
    self:player():eventBus():unsubscribeFrom(SpidertronDeleted.new(unitNumber), self)
end

function SpidertronRemoteSlot:onClick(click)
    if click:isLeft() then
        self:pick()
    elseif click:isMiddle() then
        self:clear()
    end
end

function SpidertronRemoteSlot:pick()
    if self._spidertronRemote:hasSpidertrons() and self:player():surface() ~= self._spidertronRemote:surface() then
        self:player():openInRemoteView(self._spidertronRemote:surface(), self._spidertronRemote:firstSpidertron().position)
    end
    self:player():cursor():pickSpidertronRemote(self._spidertronRemote)
    self:rememberPick()
end

---@public
---@return SpidertronRemote
function SpidertronRemoteSlot:spidertronRemote()
    return self:thing()
end

function SpidertronRemoteSlot:thing()
    return self._spidertronRemote
end

---@private
---@param unitNumber number
function SpidertronRemoteSlot:onSpidertronDelete(unitNumber)
    self:unregisterHighlightHandlers()
    self:unregisterSpidertronDeleteHandlerFor(unitNumber)

    self._spidertronRemote = self._spidertronRemote:withExcludedUnit(unitNumber)
    self:saveSpidertronRemote(self._spidertronRemote)

    self:registerHighlightHandlers()
    self:refresh()
end

---@private
---@return SpidertronRemoteButton
function SpidertronRemoteSlot:button()
    return self:child(SpidertronRemoteButton)
end

---@private
---@return SpidertronRemoteDimOverlay
function SpidertronRemoteSlot:dimOverlay()
    return self:child(SpidertronRemoteDimOverlay)
end

---@private
---@return SpidertronRemoteCountOverlay
function SpidertronRemoteSlot:countOverlay()
    return self:child(SpidertronRemoteCountOverlay)
end

---@private
---@return SpidertronRemotePlanetOverlay
function SpidertronRemoteSlot:planetOverlay()
    return self:child(SpidertronRemotePlanetOverlay)
end
