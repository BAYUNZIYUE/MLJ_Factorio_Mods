styles = data.raw["gui-style"].default

-- BUTTONS --

styles.toolbar_button_icon_black = {
    type = "button_style",
    parent = "frame_button",
    size = 20,
    left_click_sound = { { filename = "__core__/sound/gui-click.ogg", volume = 1 } }
}

styles.toolbar_button_icon_gray = {
    type = "button_style",
    parent = "toolbar_button_icon_black",
    default_graphical_set = table.deepcopy(styles.button.default_graphical_set),
    hovered_graphical_set = table.deepcopy(styles.button.hovered_graphical_set),
    clicked_graphical_set = table.deepcopy(styles.button.clicked_graphical_set),
    disabled_graphical_set = table.deepcopy(styles.button.disabled_graphical_set),
}

styles.toolbar_button_icon_green = {
    type = "button_style",
    parent = "toolbar_button_icon_black",
    default_graphical_set = table.deepcopy(styles.green_button.default_graphical_set),
    hovered_graphical_set = table.deepcopy(styles.green_button.hovered_graphical_set),
    clicked_graphical_set = table.deepcopy(styles.green_button.clicked_graphical_set),
    disabled_graphical_set = table.deepcopy(styles.green_button.disabled_graphical_set),
}

styles.toolbar_button_icon_red = {
    type = "button_style",
    parent = "toolbar_button_icon_black",
    default_graphical_set = table.deepcopy(styles.red_button.default_graphical_set),
    hovered_graphical_set = table.deepcopy(styles.red_button.hovered_graphical_set),
    clicked_graphical_set = table.deepcopy(styles.red_button.clicked_graphical_set),
    disabled_graphical_set = table.deepcopy(styles.red_button.disabled_graphical_set),

    left_click_sound = { { filename = "__core__/sound/gui-red-button.ogg", volume = 0.5 } }
}

styles.toolbar_button_text_wide_gray = {
    type = "button_style",
    parent = "button",
    font = "default-small-bold",
    left_margin = 2,
    right_margin = 2,
    left_padding = 2,
    right_padding = 2,
    height = 20,
    horizontally_stretchable = "on",
    minimal_width = 80,
    maximal_width = 10000,
}

-- ELEMENTS --

styles.toolbar_space = {
    type = "empty_widget_style",
    horizontally_stretchable = "on",
    vertically_stretchable = "on",
    left_margin = 2,
    right_margin = 2,
}

styles.toolbar_drag = {
    type = "empty_widget_style",
    parent = "draggable_space",
    horizontally_stretchable = "on",
    vertically_stretchable = "on",
    left_margin = 2,
    right_margin = 2,
}

-- CONTAINERS --

styles.toolbar_container_frame = {
    type = "frame_style",
    margin = 0,
    padding = 0,
    vertical_flow_style = {
        type = "vertical_flow_style",
        parent = "toolbar_container_vertical_flow",
    },
    horizontal_flow_style = {
        type = "horizontal_flow_style",
        parent = "toolbar_container_horizontal_flow",
    },
}

styles.toolbar_container_vertical_flow = {
    type = "vertical_flow_style",
    padding = 0,
    margin = 0,
    horizontally_stretchable = "on",
    vertically_stretchable = "on",
    vertical_spacing = 0,
}

styles.toolbar_container_horizontal_flow = {
    type = "horizontal_flow_style",
    padding = 0,
    margin = 0,
    horizontally_stretchable = "on",
    vertically_stretchable = "on",
    horizontal_spacing = 0,
}

styles.toolbar_container_header = {
    type = "horizontal_flow_style",
    parent = "toolbar_container_horizontal_flow",
    padding = 0,
    horizontal_spacing = 2
}

-- STRUCTURE --

styles.toolbar = {
    type = "frame_style",
    parent = "toolbar_container_frame",
    vertical_flow_style = table.deepcopy(styles.toolbar_container_frame.vertical_flow_style)
}
styles.toolbar.vertical_flow_style.vertical_spacing = Toolbars.styles.toolbar.spacing

styles.toolbar_header = {
    type = "horizontal_flow_style",
    parent = "toolbar_container_header",
    horizontally_stretchable = "on",
    vertically_stretchable = "on",
    top_padding = 0,
    bottom_padding = 0,
}

styles.toolbar_header_lock = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_header_unlock = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_header_align_top = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_header_align_bottom = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_header_collapse = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_header_expand = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_header_delete = {
    type = "button_style",
    parent = "toolbar_button_icon_red",
    left_click_sound = styles.toolbar_button_icon_black.left_click_sound
}

styles.toolbar_header_confirmDelete = {
    type = "button_style",
    parent = "toolbar_button_icon_red"
}

styles.toolbar_header_cancelDelete = {
    type = "button_style",
    parent = "toolbar_button_icon_green"
}

styles.toolbar_content = {
    type = "scroll_pane_style",
    parent = "naked_scroll_pane",
    extra_top_margin_when_activated = 2,
    vertical_flow_style = table.deepcopy(styles.vertical_flow),
    vertical_scrollbar_style = table.deepcopy(styles.vertical_scrollbar)
}
styles.toolbar_content.vertical_flow_style.padding = 0
styles.toolbar_content.vertical_flow_style.vertical_spacing = 0

styles.toolbar_content.vertical_scrollbar_style.width = 6
styles.toolbar_content.vertical_scrollbar_style.thumb_button_style.width = 5

styles.toolbar_content_addSection = {
    type = "button_style",
    parent = "toolbar_button_text_wide_gray",
}

styles.toolbar_content_sections = {
    type = "vertical_flow_style",
    parent = "toolbar_container_vertical_flow",
    vertical_spacing = Toolbars.styles.toolbar.content.sections.spacing,
}

styles.toolbar_content_sections_section = {
    type = "frame_style",
    parent = "toolbar_container_frame",
}

styles.toolbar_content_sections_section_header = {
    type = "horizontal_flow_style",
    parent = "toolbar_container_header",
    bottom_margin = Toolbars.styles.toolbar.content.sections.section.header.box._bottomMargin
}

styles.toolbar_content_sections_section_header_moveDown = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_content_sections_section_header_moveUp = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_content_sections_section_header_collapse = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_content_sections_section_header_expand = {
    type = "button_style",
    parent = "toolbar_button_icon_black"
}

styles.toolbar_content_sections_section_header_delete = {
    type = "button_style",
    parent = "toolbar_button_icon_red",
    left_click_sound = styles.toolbar_button_icon_black.left_click_sound
}

styles.toolbar_content_sections_section_header_confirmDelete = {
    type = "button_style",
    parent = "toolbar_button_icon_red"
}

styles.toolbar_content_sections_section_header_cancelDelete = {
    type = "button_style",
    parent = "toolbar_button_icon_green"
}

styles.toolbar_content_sections_section_header_name = {
    type = "textbox_style",
    parent = "textbox",
    font = "default-small-bold",
    disabled_font_color = gui_color.caption,
    disabled_background = {},
    left_padding = 1,
    right_padding = 1,
    height = 20,
    horizontally_stretchable = "on",
    minimal_width = 0, -- + collapse button = 2 slots, looks better when minimized with two sections
    maximal_width = 10000,
}

styles.toolbar_content_sections_section_content = {
    type = "vertical_flow_style",
    parent = "toolbar_container_vertical_flow"
}

styles.toolbar_content_sections_section_content_table = {
    type = "frame_style",
    parent = "quick_bar_inner_panel", -- for background
    horizontal_flow_style = styles.toolbar_container_horizontal_flow,
    vertical_flow_style = styles.toolbar_container_vertical_flow,
    top_margin = Toolbars.styles.toolbar.content.sections.section.content.box._topMargin,
    background_graphical_set = {
        position = { 282, 17 },
        corner_size = 8,
        overall_tiling_horizontal_padding = 4,
        overall_tiling_horizontal_size = 32,
        overall_tiling_horizontal_spacing = 8,
        overall_tiling_vertical_padding = 4,
        overall_tiling_vertical_size = 32,
        overall_tiling_vertical_spacing = 8,
    }
}

styles.toolbar_content_sections_section_content_table_row = {
    type = "horizontal_flow_style",
    parent = "toolbar_container_horizontal_flow",
}

styles.toolbar_content_sections_section_content_table_row_slot = {
    type = "empty_widget_style",
    size = 40,
}

styles.toolbar_content_sections_section_content_table_row_slot_button = {
    type = "button_style",
    parent = "slot_button",
}

styles.toolbar_content_sections_section_content_table_row_slot_button_selected = {
    type = "button_style",
    parent = "toolbar_content_sections_section_content_table_row_slot_button",
    default_graphical_set = styles.slot_button.selected_graphical_set,
    hovered_graphical_set = styles.slot_button.selected_hovered_graphical_set,
    clicked_graphical_set = styles.slot_button.selected_clicked_graphical_set
}

styles.toolbar_content_sections_section_content_table_row_slot_button_item = {
    type = "button_style",
    parent = "toolbar_content_sections_section_content_table_row_slot_button",
    left_click_sound = { { filename = "__core__/sound/gui-inventory-slot-button.ogg", volume = 0 } }
}

styles.toolbar_content_sections_section_content_table_row_slot_button_item_selected = {
    type = "button_style",
    parent = "toolbar_content_sections_section_content_table_row_slot_button_item",
    default_graphical_set = styles.toolbar_content_sections_section_content_table_row_slot_button_selected.default_graphical_set,
    hovered_graphical_set = styles.toolbar_content_sections_section_content_table_row_slot_button_selected.hovered_graphical_set,
    clicked_graphical_set = styles.toolbar_content_sections_section_content_table_row_slot_button_selected.clicked_graphical_set
}

styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_quality = {
    type = "horizontal_flow_style",
    width = 36,
    left_padding = 4,
    height = 38,
    bottom_padding = 2,
    horizontal_align = "left",
    vertical_align = "bottom"
}

styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_quality_sprite = {
    type = "image_style",
    size = 15,
    stretch_image_to_widget_size = true
}

styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_count = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_count.default_graphical_set.base.opacity = 0

--migration to 2.22.0, to remove
styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_count_zero = {
    type = "button_style",
    parent = "toolbar_content_sections_section_content_table_row_slot_item_overlay_count",
}

--migration to 2.29.0, to remove
styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_dim = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_dim.default_graphical_set.base.opacity = 0.55

styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_dim_some = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_dim_some.default_graphical_set.base.opacity = 0.1

styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_dim_none = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_item_overlay_dim_none.default_graphical_set.base.opacity = 0.5


styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_button = {
    type = "button_style",
    parent = "toolbar_content_sections_section_content_table_row_slot_button"
}

styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_button_selected = {
    type = "button_style",
    parent = "toolbar_content_sections_section_content_table_row_slot_spidertron_remote_button",
    default_graphical_set = styles.toolbar_content_sections_section_content_table_row_slot_button_selected.default_graphical_set,
    hovered_graphical_set = styles.toolbar_content_sections_section_content_table_row_slot_button_selected.hovered_graphical_set,
    clicked_graphical_set = styles.toolbar_content_sections_section_content_table_row_slot_button_selected.clicked_graphical_set
}

styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_count = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_count.default_graphical_set.base.opacity = 0

styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_same_surface = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_same_surface.default_graphical_set.base.opacity = 0.1

styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_other_surface = {
    type = "button_style",
    parent = "slot_button",
    default_graphical_set = table.deepcopy(styles.slot_button.default_graphical_set),
}
styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_dim_other_surface.default_graphical_set.base.opacity = 0.55

styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_planet = {
    type = "horizontal_flow_style",
    left_padding = 4,
    width = 36,
    top_padding = 4,
    height = 36,
    horizontal_align = "left",
    vertical_align = "top"
}

styles.toolbar_content_sections_section_content_table_row_slot_spidertron_remote_overlay_planet_sprite = {
    type = "image_style",
    size = 16,
    stretch_image_to_widget_size = true
}


styles.toolbar_content_sections_section_content_table_row_slot_entities_overlay_one = {
    type = "vertical_flow_style",
    size = 40,
    horizontal_align = "center",
    vertical_align = "center",
}

styles.toolbar_content_sections_section_content_table_row_slot_entities_overlay_one_sprite = {
    type = "empty_widget_style", -- "sprite"
    size = 23
}

styles.toolbar_content_sections_section_content_table_row_slot_entities_overlay_many = {
    type = "vertical_flow_style",
}

styles.toolbar_content_sections_section_content_table_row_slot_entities_overlay_many_table = {
    type = "table_style",
}

styles.toolbar_content_sections_section_content_table_row_slot_entities_overlay_many_table_sprite = {
    type = "empty_widget_style", -- "sprite"
    size = 14
}
