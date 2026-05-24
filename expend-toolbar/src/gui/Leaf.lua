import("gui.Sized")

---@class Leaf : Sized
Leaf = Sized:extendAs("gui.Leaf")

function Leaf.new(parent, root)
    return Leaf:super(Sized.new(parent, root))
end

function Leaf:freshWidth()
    return self:box():totalWidth()
end

function Leaf:freshDisplayWidth()
    if not self:isVisible() then
        return 0
    end
    return self:box():scale(self:display():scaleValue()):totalWidth()
end

function Leaf:freshHeight()
    return self:box():totalHeight()
end

function Leaf:freshDisplayHeight()
    if not self:isVisible() then
        return 0
    end
    return self:box():scale(self:display():scaleValue()):totalHeight()
end
