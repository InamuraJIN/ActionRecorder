"""only relative import from intra-modules: ui, shared_data"""

from .categories import (
    read_category_visibility,
    get_category_id
)

from .globals import (
    save,
    load,
    import_global_from_dict,
    get_global_action_id,
    get_global_action_ids,
    add_empty_action_keymap,
    is_action_keymap_empty,
    get_action_keymap,
    remove_action_keymap,
    get_all_action_keymaps
)

from .locals import (
    save_local_to_scene,
    get_local_action_index,
    load_local_action,
    local_action_to_text,
    remove_local_action_from_text
)

from .macros import (
    get_local_macro_index,
    add_report_as_macro,
    get_report_text,
    split_context_report,
    create_object_copy,
    improve_context_report,
    split_operator_report,
    evaluate_operator,
    improve_operator_report,
    dict_to_kwarg_str,
    track_scene,
    merge_report_tracked,
    compare_op_dict,
    convert_value_to_python
)

from .shared import (
    check_for_duplicates,
    add_data_to_collection,
    insert_to_collection,
    swap_collection_items,
    property_to_python,
    apply_data_to_item,
    get_name_of_command,
    update_command,
    play,
    get_font_path,
    split_and_keep,
    text_to_lines,
    execute_render_complete,
    enum_list_id_to_name_dict,
    enum_items_to_enum_prop_list,
    install_packages,
    get_preferences,
    get_categorized_view_3d_modes,
    get_attribute,
    get_attribute_default
)
