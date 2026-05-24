import("Thing")

---@class SimpleTool : Thing
SimpleTool = Thing:extendAs("SimpleTool")

---@public
---@param name string
function SimpleTool.new(name)
    return SimpleTool:super(Thing.new(name))
end
