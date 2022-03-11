# region UI functions
def draw_global_action(layout, AR, id: str) -> None:
    action = AR.global_actions[id]
    row = layout.row(align=True)
    row.alert = action.alert
    row.prop(action, 'selected', toggle = 1, icon= 'LAYER_ACTIVE' if action.selected else 'LAYER_USED', text= "", event= True)
    op = row.operator("ar.global_icon", text= "", icon_value= action.icon if action.icon else 101)
    op.id = id
    op = row.operator("ar.global_execute_action", text= action.label)
    op.id = id
# endregion