import("factorio.events.general.Tick")

---@class Scheduler : Object
---@field private _eventBus EventBus
Scheduler = Object:extendAs("Scheduler")

---@public
---@generic V
---@param eventBus EventBus
---@return Scheduler<V>
function Scheduler.new(eventBus)
    local this = Scheduler:super(Object.new())
    this._eventBus = eventBus
    return this
end

---@public
---@param delayInTicks number
---@param task fun():void
---@param requester table
function Scheduler:schedule(requester, delayInTicks, task)
    delayInTicks = math.ceil(delayInTicks)
    if delayInTicks <= 0 then
        task()
    else
        local executionTick = Tick.new(game.tick + delayInTicks)
        self._eventBus:subscribeTo(
                executionTick,
                requester,
                function()
                    self._eventBus:unsubscribeFrom(executionTick, requester)
                    task()
                end
        )
    end
end

---@public
---@param requester table
function Scheduler:cancelAll(requester)
    self._eventBus:unsubscribeFromAll(requester)
end
