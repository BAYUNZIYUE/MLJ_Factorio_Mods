---@class Time : Object
---@field private __tick number
Time = Object:extendAs("lang.Time")

---@public
---@param millis number
---@return number ticks
function Time.millisToTicks(millis)
    return math.ceil(millis / 16.6)
end
