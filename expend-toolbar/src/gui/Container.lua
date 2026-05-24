import("gui.Sized")

---@class Container : Sized
Container = Sized:extendAs("gui.Container")

function Container.new(parent, element, childrenClasses)
    return Container:super(Sized.new(parent, element, childrenClasses))
end

--function Container:addChild(child)
--fireSizeChanged() is execute in Sized.create() when the child is fully initialized as Sized object
--end

function Container:removeChild(childToRemove)
    Container:super().removeChild(self, childToRemove)
    self:fireSizeChange()
end
