---@class EventBus : Object
---@field private _topics table<Event, table<Object, fun(event: Event):void>>
---@field private _subscribersTopics table<Object, string>
EventBus = Object:extendAs("EventBus")

function EventBus.new()
    local this = EventBus:super(Object.new())
    this._topics = {}
    this._subscribersTopics = {}
    return this
end

---@public
---@generic E : Event
---@param event E
---@param subscriber Object
---@param handler fun(event: E):void
function EventBus:subscribeTo(event, subscriber, handler)
    local topic = event:topic()
    if not self._topics[topic] then
        self._topics[topic] = {}
    end
    self._topics[topic][subscriber] = handler

    if not self._subscribersTopics[subscriber] then
        self._subscribersTopics[subscriber] = {}
    end
    self._subscribersTopics[subscriber][topic] = self._topics[topic]
end

---@public
---@param event Event
function EventBus:publish(event)
    local subscribers = self._topics[event:topic()]
    if subscribers then
        for _, handler in pairs(subscribers) do
            handler(event)
        end
    end
end

---@public
---@param event Event
---@param toUnsubscribe Object
function EventBus:unsubscribeFrom(event, toUnsubscribe)
    local topic = self._topics[event:topic()]
    if topic and topic[toUnsubscribe] then
        topic[toUnsubscribe] = nil
        self._subscribersTopics[toUnsubscribe][event:topic()] = nil
    end
end

---@public
---@param toUnsubscribe Object
function EventBus:unsubscribeFromAll(toUnsubscribe)
    local topics = self._subscribersTopics[toUnsubscribe]
    if topics then
        self._subscribersTopics[toUnsubscribe] = nil

        for _, topic in pairs(topics) do
            if topic[toUnsubscribe] then
                topic[toUnsubscribe] = nil
            end
        end
    end
end

---@public
---@param event Event
function EventBus:hasSubscribersFor(event)
    local topic = self._topics[event:topic()]
    return topic and next(topic) ~= nil
end
