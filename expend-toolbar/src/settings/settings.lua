data:extend({
                {
                    order = "a1",
                    name = Toolbars.settings.crafting,
                    localised_name = "Crafting (controls reconfiguration required)",
                    localised_description = LocalisedText.new()
                                                         :append("Due to modding limitations (mod controls same as game controls are not triggered over GUI) following game controls are reused:"):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append({ "controls.craft" }):append(RichText.fontEnd()):append(" ("):append({ "controls.craft" }):append(")"):append(RichText.fontSemibold(": ")):append({ "key-sequences.craft" }):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append({ "controls.craft-5" }):append(RichText.fontEnd()):append(" ("):append({ "controls.craft-5" }):append(")"):append(RichText.fontSemibold(": ")):append({ "key-sequences.craft-5" }):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append({ "controls.stack-transfer" }):append(RichText.fontEnd()):append(" ("):append({ "gui-permissions-names.Craft" }):append(" "):append({ "description.stack-size" }):append(")"):append(RichText.fontSemibold(": ")):append({ "key-sequences.stack-transfer" }):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append({ "controls.stack-split" }):append(RichText.fontEnd()):append(" ("):append({ "gui-permissions-names.Craft" }):append(" "):append({ "description.stack-size" }):append("/2"):append(")"):append(RichText.fontSemibold(": ")):append({ "key-sequences.stack-split" }):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append({ "controls.craft-all" }):append(RichText.fontEnd()):append(" ("):append({ "controls.craft-all" }):append(")"):append(RichText.fontSemibold(": ")):append({ "key-sequences.craft-all" }):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append({ "controls.inventory-split" }):append(RichText.fontEnd()):append(" ("):append({ "controls.craft-all" }):append("/2"):append(")"):append(RichText.fontSemibold(": ")):append({ "key-sequences.inventory-split" }):appendNewLine()

                                                         :appendNewLine()
                                                         :append("Example configuration:"):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append("*"):append({ "controls.craft" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Left-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append("*"):append({ "controls.craft-5" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Right-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append("*"):append({ "controls.craft-all" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Shift + Left-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.cancel-craft" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Left-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.cancel-craft-5" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Right-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.cancel-craft-all" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Shift + Left-click")):appendNewLine()

                                                         :append(RichText.fontSemiboldStart()):append("*"):append({ "controls.stack-transfer" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Alt + Left-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.inventory-transfer" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Shift + Left-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.fast-entity-transfer" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Alt + Left-click")):appendNewLine()

                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.cursor-split" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Right-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append("*"):append({ "controls.stack-split" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Alt + Right-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append("*"):append({ "controls.inventory-split" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Shift + Right-click")):appendNewLine()
                                                         :append(RichText.fontSemiboldStart()):append(" "):append({ "controls.fast-entity-split" }):append(": "):append(RichText.fontEnd()):append(RichText.keySequence("Control + Alt + Right-click")):appendNewLine()

                                                         :append(RichText.fontSemibold("*")):append(" - required")
                                                         :localisedString(),
                    setting_type = "runtime-per-user",
                    type = "bool-setting",
                    default_value = false,
                },
                {
                    order = "a2",
                    name = Toolbars.settings.tooltipDelay,
                    localised_name = "Tooltip delay [ms]",
                    setting_type = "runtime-per-user",
                    type = "int-setting",
                    default_value = 600,
                },
                {
                    order = "a3",
                    name = Toolbars.settings.tooltipRefreshInterval,
                    localised_name = "Tooltip refresh interval [tick=16.6ms]",
                    setting_type = "runtime-per-user",
                    type = "int-setting",
                    default_value = 5,
                },
                {
                    order = "a4",
                    name = Toolbars.settings.showControlsInTheTooltip,
                    localised_name = "Show controls in the tooltip",
                    setting_type = "runtime-per-user",
                    type = "bool-setting",
                    default_value = true,
                },
                {
                    order = "b1",
                    name = Toolbars.settings.characterInventoriesContentRefreshInterval,
                    localised_name = "Character inventories content refresh interval [tick=16.6ms]",
                    localised_description = "Find your tradeoff between character inventories refresh cost, responsiveness and slots count change cost",
                    setting_type = "runtime-per-user",
                    type = "int-setting",
                    default_value = 1,
                },
                {
                    order = "c1",
                    name = Toolbars.settings.showVehicleInventoriesContent,
                    localised_name = "Show vehicle inventories content",
                    localised_description = "Turn it off if you don’t like it or want to avoid its performance cost",
                    setting_type = "runtime-per-user",
                    type = "bool-setting",
                    default_value = true,
                },
                {
                    order = "c2",
                    name = Toolbars.settings.vehicleInventoriesContentRefreshInterval,
                    localised_name = "Vehicle inventories content refresh interval [tick=16.6ms]",
                    localised_description = "Find your tradeoff between vehicle inventories content refresh cost, responsiveness and slots count change cost",
                    setting_type = "runtime-per-user",
                    type = "int-setting",
                    default_value = 5,
                },
                {
                    order = "d1",
                    name = Toolbars.settings.showLogisticNetworksContent,
                    localised_name = "Show logistic networks content",
                    localised_description = "Turn it off if you don’t like it or want to avoid its performance cost",
                    setting_type = "runtime-per-user",
                    type = "bool-setting",
                    default_value = true,
                },
                {
                    order = "d2",
                    name = Toolbars.settings.logisticNetworksContentRefreshInterval,
                    localised_name = "Logistic networks content refresh interval [tick=16.6ms]",
                    localised_description = "Find your tradeoff between logistic networks content refresh cost, responsiveness and slots count change cost",
                    setting_type = "runtime-per-user",
                    type = "int-setting",
                    default_value = 5,
                },
            })
