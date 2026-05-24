import("factorio.RecipePrototypes")
import("player.Player")
import("player.Recipes")

remote.add_interface(Toolbars.name, {
    printCursorContent = function(player_index)
        ---@type LuaPlayer
        local luaPlayer = game.players[player_index]
        Log.log("Holding:")
        if luaPlayer.cursor_record and luaPlayer.cursor_record.valid then
            local info = {
                type = luaPlayer.cursor_record.type,
                objectName = luaPlayer.cursor_record.object_name,
            }
            Log.log(info)
        end
        if luaPlayer.cursor_stack and luaPlayer.cursor_stack.valid_for_read then
            local info = {
                type = luaPlayer.cursor_stack.type,
                name = luaPlayer.cursor_stack.name,
                quality = luaPlayer.cursor_stack.quality.name,
                count = luaPlayer.cursor_stack.count,
                label = luaPlayer.cursor_stack.label,
                itemNumber = luaPlayer.cursor_stack.item_number,
                isSelectionTool = luaPlayer.cursor_stack.is_selection_tool,
                isItemWithEntityData = luaPlayer.cursor_stack.is_item_with_entity_data,
                isItemWithTags = luaPlayer.cursor_stack.is_item_with_tags,
            }
            Log.log(info)
            ---@param entity LuaEntity
            if luaPlayer.spidertron_remote_selection then
                for i, entity in ipairs(luaPlayer.spidertron_remote_selection) do
                    Log.log(entity.unit_number)
                end
            end
        end
    end,

    describeRecipesForAnItem = function(player_index, itemProductName)
        local recipes = Player.get(player_index):recipes()

        Log.log("")
        Log.log("Character crafting categories:")
        for categoryName, _ in pairs(recipes._characterCraftingCategories) do
            Log.log(categoryName)
        end
        Log.log("")

        local recipesNames = RecipePrototypes.instance():findRecipePrototypesNamesByItemProductName(itemProductName)
        for _, recipeName in ipairs(recipesNames) do
            ---@type LuaRecipePrototype
            local prototype = prototypes.recipe[recipeName]
            Log.log("")
            Log.log("Recipe name:" .. prototype.name)
            Log.log("Enabled: " .. tostring(game.players[player_index].force.recipes[prototype.name].enabled))
            Log.log("Category: " .. prototype.category)
            Log.log("Main product:")
            Log.log(prototype.main_product)
            --Log.log("Allow intermediates: " .. tostring(prototype.allow_intermediates))
            --Log.log("Allow as intermediate: " .. tostring(prototype.allow_as_intermediate))
            Log.log("Products:")
            Log.log(prototype.products)
            Log.log("Ingredients:")
            Log.log(prototype.ingredients)
        end
    end,

    testTagSize = function(player_index)
        local stack = Player.get(player_index):luaPlayer().cursor_stack
        local value = "1111111111"
        local toolbarString = ""
        for _ = 1, 100000 do
            toolbarString = toolbarString .. value
        end
        stack.set_stack({ name = "blueprint" })
        local entities = {}
        entities[1] = {
            entity_number = 1, name = "constant-combinator", position = { 0, 0 },
            tags = { toolbar = toolbarString }
        }
        stack.set_blueprint_entities(entities)
        local retrievedToolbarString = stack.get_blueprint_entities()[1].tags.toolbar
        Log.log(toolbarString == retrievedToolbarString)
        Log.log(string.len(toolbarString))
    end,
}
)
