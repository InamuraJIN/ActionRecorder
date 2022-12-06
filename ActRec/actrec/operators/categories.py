# region Imports
# externals modules
from collections import defaultdict

# blender modules
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, IntProperty

# relative imports
from .. import functions, ui_functions
from . import shared
from ..functions.shared import get_preferences
# endregion


# region Operators


class AR_OT_category_interface(Operator):

    """import bpy
        try:
            bpy.context.area.ui_type = ""
        except TypeError as err:
            enum_items = eval(str(err).split('enum "" not found in ')[1])
            current_ui_type = bpy.context.area.ui_type
            my_dict = {}
            for item in enum_items:
                bpy.context.area.ui_type = item
                if "UI" in [region.type for region in bpy.context.area.regions]: #only if ui_type has region UI
                    my_dict[item] = bpy.context.area.type
            print(my_dict)
            bpy.context.area.ui_type = current_ui_type
    """  # code to get areas_to_spaces
    # don't use it, because it's based on an error message and it doesn't contains enough data
    areas_to_spaces_with_mode = {
        'VIEW_3D': 'VIEW_3D',
        'IMAGE_EDITOR': 'IMAGE_EDITOR',
        'UV': 'IMAGE_EDITOR',
        'CompositorNodeTree': 'NODE_EDITOR',
        'TextureNodeTree': 'NODE_EDITOR',
        'GeometryNodeTree': 'NODE_EDITOR',
        'ShaderNodeTree': 'NODE_EDITOR',
        'SEQUENCE_EDITOR': 'SEQUENCE_EDITOR',
        'CLIP_EDITOR': 'CLIP_EDITOR',
        'DOPESHEET': 'DOPESHEET_EDITOR',
        'TIMELINE': 'DOPESHEET_EDITOR',
        'FCURVES': 'GRAPH_EDITOR',
        'DRIVERS': 'GRAPH_EDITOR',
        'NLA_EDITOR': 'NLA_EDITOR',
        'TEXT_EDITOR': 'TEXT_EDITOR'
    }

    modes = {
        'VIEW_3D': functions.enum_items_to_enum_prop_list(
            bpy.ops.object.mode_set.get_rna_type().bl_rna.properties[1].enum_items
        ),
        'IMAGE_EDITOR': functions.enum_items_to_enum_prop_list(
            bpy.types.SpaceImageEditor.bl_rna.properties['ui_mode'].enum_items
        ),
        'NODE_EDITOR': functions.enum_items_to_enum_prop_list(
            bpy.types.SpaceNodeEditor.bl_rna.properties['texture_type'].enum_items
        ),
        'SEQUENCE_EDITOR': functions.enum_items_to_enum_prop_list(
            bpy.types.SpaceSequenceEditor.bl_rna.properties['view_type'].enum_items
        ),
        'CLIP_EDITOR': functions.enum_items_to_enum_prop_list(
            bpy.types.SpaceClipEditor.bl_rna.properties['mode'].enum_items
        ),
        'DOPESHEET_EDITOR': functions.enum_items_to_enum_prop_list(
            bpy.types.SpaceDopeSheetEditor.bl_rna.properties['ui_mode'].enum_items
        ),
        'GRAPH_EDITOR': functions.enum_items_to_enum_prop_list(
            bpy.types.SpaceGraphEditor.bl_rna.properties['mode'].enum_items
        )
    }

    for key, item in modes.items():
        modes[key] = [("all", "All", "use in all available modes", "GROUP_VCOL", 0)] + item

    mode_dict = {area: functions.enum_list_id_to_name_dict(data) for area, data in modes.items()}

    area_items = [  # (identifier, name, description, icon, value)
        ('', 'General', ''),
        ('VIEW_3D', '3D Viewport', '', 'VIEW3D', 0),
        ('IMAGE_EDITOR', 'Image Editor', '', 'IMAGE', 1),
        ('UV', 'UV Editor', '', 'UV', 2),
        ('CompositorNodeTree', 'Compositor', '', 'NODE_COMPOSITING', 3),
        ('TextureNodeTree', 'Texture Node Editor', '', 'NODE_TEXTURE', 4),
        ('GeometryNodeTree', 'Geomerty Node Editor', '', 'NODETREE', 5),
        ('ShaderNodeTree', 'Shader Editor', '', 'NODE_MATERIAL', 6),
        ('SEQUENCE_EDITOR', 'Video Sequencer', '', 'SEQUENCE', 7),
        ('CLIP_EDITOR', 'Movie Clip Editor', '', 'TRACKER', 8),

        ('', 'Animation', ''),
        ('DOPESHEET', 'Dope Sheet', '', 'ACTION', 9),
        ('TIMELINE', 'Timeline', '', 'TIME', 10),
        ('FCURVES', 'Graph Editor', '', 'GRAPH', 11),
        ('DRIVERS', 'Drivers', '', 'DRIVER', 12),
        ('NLA_EDITOR', 'Nonlinear Animation', '', 'NLA', 13),

        ('', 'Scripting', ''),
        ('TEXT_EDITOR', 'Text Editor', '', 'TEXT', 14)
    ]
    area_dict = functions.enum_list_id_to_name_dict(area_items)

    def mode_items(self, context: bpy.types.Context) -> list:
        """
        get all available modes for the selected area (self.area)

        Args:
            context (bpy.types.Context): active blender context

        Returns:
            list: modes of the area
        """
        return AR_OT_category_interface.modes.get(
            AR_OT_category_interface.areas_to_spaces_with_mode[self.area], []
        )

    label: StringProperty(name="Category Label", default="Untitled")
    area: EnumProperty(
        items=area_items,
        name="Area",
        description="Shows all available areas for the panel"
    )
    mode: EnumProperty(
        items=mode_items,
        name="Mode",
        description="Shows all available modes for the selected area"
    )

    category_visibility = []

    def apply_visibility(self, ActRec_pref: bpy.types.AddonPreferences, category_visibility: list, id: str):
        """
        applies visibility for the selected category

        Args:
            ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
            category_visibility (list): list of pattern (area, mode) where the category should be visible
            id (str): id of the category to select
        """
        # REFACTOR indentation
        category = ActRec_pref.categories[id]
        visibility = defaultdict(list)
        for area, mode in category_visibility:
            visibility[area].append(mode)
        for area, modes in visibility.items():
            new_area = category.areas.add()
            new_area.type = area
            if 'all' not in modes:
                for mode in modes:
                    new_mode = new_area.modes.add()
                    new_mode.type = mode

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.prop(self, 'label', text="Label")
        layout.prop(self, 'area')
        if len(self.mode_items(context)):
            layout.prop(self, 'mode')
        ops = layout.operator(AR_OT_category_apply_visibility.bl_idname)
        ops.area = self.area
        ops.mode = self.mode
        cls = AR_OT_category_interface
        # REFACTOR indentation
        if len(cls.category_visibility) > 0:
            box = layout.box()
            row = box.row()
            row.label(text="Area")
            row.label(text="Mode")
            row.label(icon='BLANK1')
            for i, (area, mode) in enumerate(cls.category_visibility):
                row = box.row()
                row.label(text=cls.area_dict[area])
                mode_str = ""
                area_modes = cls.mode_dict.get(area)
                if area_modes:
                    mode_str = area_modes[mode]
                row.label(text=mode_str)
                row.operator(
                    AR_OT_category_delete_visibility.bl_idname,
                    text='',
                    icon='PANEL_CLOSE',
                    emboss=False
                ).index = i


class AR_OT_category_add(AR_OT_category_interface, Operator):
    bl_idname = "ar.category_add"
    bl_label = "Add Category"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        AR_OT_category_interface.category_visibility.clear()
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        new = ActRec_pref.categories.add()
        new.label = functions.check_for_duplicates([c.label for c in ActRec_pref.categories], self.label)
        self.apply_visibility(ActRec_pref, AR_OT_category_interface.category_visibility, new.id)
        ui_functions.register_category(ActRec_pref, len(ActRec_pref.categories) - 1)
        context.area.tag_redraw()
        functions.category_runtime_save(ActRec_pref)
        return {"FINISHED"}


class AR_OT_category_edit(shared.Id_based, AR_OT_category_interface, Operator):
    bl_idname = "ar.category_edit"
    bl_label = "Edit Category"
    bl_description = "Edit the selected Category"

    cancel_data = {}
    ignore_selection = False

    @classmethod
    def poll(cls, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.categories)
            and (ignore
                 or ui_functions.category_visible(
                     ActRec_pref,
                     context,
                     ActRec_pref.categories[ActRec_pref.selected_category]
                 ))
        )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        ActRec_pref = get_preferences(context)
        id = self.id = functions.get_category_id(ActRec_pref, self.id, self.index)
        category = ActRec_pref.categories.get(id, None)
        if category:
            AR_OT_category_interface.category_visibility = functions.read_category_visibility(ActRec_pref, id)
            return context.window_manager.invoke_props_dialog(self)
        return {'CANCELLED'}

    def execute(self, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        category = ActRec_pref.categories[self.id]
        category.areas.clear()
        self.apply_visibility(
            ActRec_pref, AR_OT_category_interface.category_visibility, self.id)
        functions.category_runtime_save(ActRec_pref)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_category_apply_visibility(Operator):
    bl_idname = "ar.category_apply_visibility"
    bl_label = "Apply Visibility"
    bl_description = ""
    bl_options = {"INTERNAL"}

    mode: StringProperty()
    area: StringProperty()

    def execute(self, context: bpy.types.Context):
        AR_OT_category_interface.category_visibility.append((self.area, self.mode))
        return {"FINISHED"}


class AR_OT_category_delete_visibility(Operator):
    bl_idname = "ar.category_delete_visibility"
    bl_label = "Delete Visibility"
    bl_description = ""
    bl_options = {"INTERNAL"}

    index: IntProperty()

    def execute(self, context: bpy.types.Context):
        AR_OT_category_interface.category_visibility.pop(self.index)
        return {"FINISHED"}


class AR_OT_category_delete(shared.Id_based, Operator):
    bl_idname = "ar.category_delete"
    bl_label = "Delete Category"
    bl_description = "Delete the selected Category"

    ignore_selection = False

    @classmethod
    def poll(cls, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.categories)
            and (ignore
                 or ui_functions.category_visible(
                     ActRec_pref,
                     context,
                     ActRec_pref.categories[ActRec_pref.selected_category]
                 ))
        )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        categories = ActRec_pref.categories
        id = functions.get_category_id(ActRec_pref, self.id, self.index)
        self.clear()
        category = categories.get(id, None)
        # REFACTOR indentation
        if category:
            category = categories[id]
            for id_action in category.actions:
                ActRec_pref.global_actions.remove(ActRec_pref.global_actions.find(id_action.id))
            ui_functions.unregister_category(ActRec_pref, len(categories) - 1)
            categories.remove(categories.find(id))
            if len(categories):
                categories[0].selected = True
            context.area.tag_redraw()
            functions.category_runtime_save(ActRec_pref)
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(
            text="All Actions in this Category will be deleted", icon='ERROR')


class AR_OT_category_move_up(shared.Id_based, Operator):
    bl_idname = "ar.category_move_up"
    bl_label = "Move Up"
    bl_description = "Move the Category up"

    ignore_selection = False

    @classmethod
    def poll(cls, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return len(ActRec_pref.categories) and (ignore or ui_functions.category_visible(
            ActRec_pref, context, ActRec_pref.categories[ActRec_pref.selected_category]))

    def execute(self, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        id = functions.get_category_id(ActRec_pref, self.id, self.index)
        self.clear()
        categories = ActRec_pref.categories
        i = categories.find(id)
        y = i - 1  # upper index
        # REFACTOR indentation
        if i >= 0 and y >= 0 and ui_functions.category_visible(ActRec_pref, context, categories[i]):
            swap_category = categories[y]
            # get next visible category
            while not ui_functions.category_visible(ActRec_pref, context, swap_category):
                y -= 1
                if y < 0:
                    return {"CANCELLED"}
                swap_category = categories[y]
            functions.swap_collection_items(categories, i, y)
            ActRec_pref.categories[y].selected = True
            context.area.tag_redraw()
            functions.category_runtime_save(ActRec_pref)
            return {"FINISHED"}
        return {'CANCELLED'}


class AR_OT_category_move_down(shared.Id_based, Operator):
    bl_idname = "ar.category_move_down"
    bl_label = "Move Down"
    bl_description = "Move the Category down"

    ignore_selection = False

    @classmethod
    def poll(cls, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.categories)
            and (ignore
                 or ui_functions.category_visible(
                     ActRec_pref,
                     context,
                     ActRec_pref.categories[ActRec_pref.selected_category]
                 ))
        )

    def execute(self, context: bpy.types.Context):
        ActRec_pref = get_preferences(context)
        id = functions.get_category_id(ActRec_pref, self.id, self.index)
        self.clear()
        categories = ActRec_pref.categories
        i = categories.find(id)
        y = i + 1  # lower index
        if i >= 0 and y < len(categories) and ui_functions.category_visible(ActRec_pref, context, categories[i]):
            swap_category = categories[y]
            # get next visible category
            while not ui_functions.category_visible(ActRec_pref, context, swap_category):
                y += 1
                if y >= len(categories):
                    return {"CANCELLED"}
                swap_category = categories[y]
            functions.swap_collection_items(categories, i, y)
            ActRec_pref.categories[y].selected = True
            context.area.tag_redraw()
            functions.category_runtime_save(ActRec_pref)
            return {"FINISHED"}
        return {'CANCELLED'}
# endregion


classes = [
    AR_OT_category_add,
    AR_OT_category_edit,
    AR_OT_category_apply_visibility,
    AR_OT_category_delete_visibility,
    AR_OT_category_delete,
    AR_OT_category_move_up,
    AR_OT_category_move_down
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
