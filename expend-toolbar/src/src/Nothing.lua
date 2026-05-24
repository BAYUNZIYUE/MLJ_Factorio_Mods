import("Thing")

---@class Nothing : Thing
Nothing = Thing:extendAs("Nothing")

---@public
function Nothing.new()
    return Nothing:super(Thing.new("nothing"))
end
