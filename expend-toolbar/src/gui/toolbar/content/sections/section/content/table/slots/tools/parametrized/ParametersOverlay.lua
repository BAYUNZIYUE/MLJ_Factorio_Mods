import("gui.Component")

---@class ParametersOverlay : Component
ParametersOverlay = Component:extendAs("gui.toolbar.content.sections.section.content.table.slots.tools.parametrized.ParametersOverlay")

---@param parameters table<string>
function ParametersOverlay.create(parent, parameters)
    return Component.create(
            ParametersOverlay,
            parent, {
                type = "empty-widget",
            }
    )
end

function ParametersOverlay.new(parent, root)
    return ParametersOverlay:super(Component.new(parent, root))
end
