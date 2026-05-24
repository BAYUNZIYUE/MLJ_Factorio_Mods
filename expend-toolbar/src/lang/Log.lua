---@class Log : Object
Log = Object:extendAs("lang.Log")
Log.__on = true
Log.__inGame = true
Log.__logTick = false
Log.__lastTick = -1

---@public
function Log.logTick()
    Log.log(game.tick)
end

---@public
function Log.logMethod()
    local info = debug.getinfo(2, "n")
    local name = info and info.name or "unknown"
    Log.log(name .. "()")
end

---@public
function Log.logTrace()
    Log.log(debug.traceback())
end

---@public
---@param prefix string
function Log.logTraceWith(prefix)
    Log.log(prefix .. "\n" .. debug.traceback())
end

---@public
---@param message string|number|table|userdata
function Log.log(message)
    if Log.__on then
        if Log.__logTick then
            local tick = game.tick
            if tick > Log.__lastTick then
                Log.append("")
                Log.append("Tick: " .. tick)
                Log.__lastTick = tick
            end
        end
        Log.append(message)
    end
end

---@private
---@param message string|number|table|userdata
function Log.append(message)
    local entry
    if type(message) == "userdata" then
        entry = message
    elseif type(message) == "table" then
        entry = serpent.block(message, { comment = false })
    else
        entry = tostring(message)
    end
    if Log.__inGame then
        game.print(entry, { skip = defines.print_skip.never })
    end
    log(entry)
end
