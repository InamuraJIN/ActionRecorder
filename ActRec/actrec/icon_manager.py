# region Imports
# external modules
import os

# blender modules
import bpy
import bpy.utils.previews
from bpy.types import Operator, PropertyGroup
from bpy.props import IntProperty, StringProperty, BoolProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper

# relative imports
from .log import logger
from .functions.shared import get_preferences
from . import functions
# endregion

preview_collections = {}

# region functions


def get_icons_values() -> list[int]:
    """
    get all default icons of Blender as values except the icon 'NONE' (value: 0)

    Returns:
        list[int]: list of icon values
    """
    return [icon.value for icon in
            bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.values()[1:]]


def get_icons_names() -> list[str]:
    """
    get all default icon of Blender as name except the icon 'NONE' (value: 0)

    Returns:
        list[str]: list of icon names
    """
    return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()[1:]


def load_icons(ActRec_pref: bpy.types.Preferences):
    """
    loads all saved icons from the icon folder, which can be located by the user.
    the icon are saved as png and with their icon name
    supported blender image formats https://docs.blender.org/manual/en/latest/files/media/image_formats.html

    Args:
        ActRec_pref (bpy.types.Preferences): preferences of this addon
    """
    directory = ActRec_pref.icon_path
    for icon in os.listdir(directory):
        filepath = os.path.join(directory, icon)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            register_icon(
                preview_collections['ar_custom'],
                "AR_%s" % ".".join(icon.split(".")[:-1]), filepath, True
            )


def load_icon(ActRec_pref: bpy.types.Preferences, filepath: str, only_new: bool = False):
    """
    load image form filepath as custom addon icon and resize to 32x32 (Blender icon size)
    supported blender image formats https://docs.blender.org/manual/en/latest/files/media/image_formats.html

    Args:
        ActRec_pref (bpy.types.Preferences): preferences of this addon
        filepath (str): filepath to the image file
        only_new (bool, optional): if icon is already register by name, it won't be registered again. Defaults to False.
    """
    # uses Blender image to convert to other image format and resize to icon size
    image = bpy.data.images.load(filepath)
    image.scale(32, 32)
    name = os.path.splitext(image.name)[0]  # name without file extension
    # image.name has format included
    internal_path = os.path.join(ActRec_pref.icon_path, image.name)
    image.save_render(internal_path)  # save Blender image to inside the icon folder
    register_icon(preview_collections['ar_custom'], "AR_%s" % name, internal_path, only_new)
    bpy.data.images.remove(image)


def register_icon(preview_collection: bpy.utils.previews.ImagePreviewCollection,
                  name: str,
                  filepath: str,
                  only_new: bool):
    """
    adds image form filepath to the addon icon collection with a custom name

    Args:
        preview_collection (bpy.utils.previews.ImagePreviewCollection): collection to add icon to
        name (str): name of the icon
        filepath (str): filepath to the image file
        only_new (bool): if icon is already register by name, it won't be registered again.
    """
    if only_new and not (name in preview_collection) or not only_new:
        name = functions.check_for_duplicates(preview_collection, name)
        preview_collection.load(name, filepath, 'IMAGE', force_reload=True)
        logger.info("Custom Icon <%s> registered" % name)


def unregister_icon(preview_collection: bpy.utils.previews.ImagePreviewCollection, name: str):
    """
    deletes icon by name from given collection if possible

    Args:
        preview_collection (bpy.utils.previews.ImagePreviewCollection): collection to add icon to
        name (str): name of the icon
    """
    if name in preview_collection:
        del preview_collection[name]
# endregion

# region Operators


class Icontable(Operator):
    bl_label = "Icons"
    bl_description = "Press to select an Icon"

    search: StringProperty(
        name="Icon Search",
        description="search Icon by name",
        options={'TEXTEDIT_UPDATE'}
    )
    default_icon_value: IntProperty(
        name="Default Icon",
        description="Default icon that get set when clear is pressed",
        default=0
    )
    reuse: BoolProperty(
        name="Reuse",
        description="Reuse the last selected icon"
    )

    def draw(self, context):
        ActRec_pref = get_preferences(context)
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text="Selected Icon:")
        row.label(text=" ", icon_value=ActRec_pref.selected_icon)
        row.prop(self, 'search', text='Search:')
        row.operator('ar.icon_selector',
                     text="Clear Icon").icon = self.default_icon_value
        box = layout.box()
        grid_flow = box.grid_flow(row_major=True, columns=35,
                                  even_columns=True, even_rows=True, align=True)
        icon_values = get_icons_values()
        for i, icon_name in enumerate(get_icons_names()):
            human_name = icon_name.lower().replace("_", " ")
            if self.search == '' or self.search.lower() in human_name:
                grid_flow.operator('ar.icon_selector', text="",
                                   icon_value=icon_values[i]).icon = icon_values[i]
        box = layout.box()
        row = box.row().split(factor=0.5)
        row.label(text="Custom Icons")
        row2 = row.row()
        row2.operator('ar.add_custom_icon', text="Add Custom Icon",
                      icon='PLUS').activate_pop_up = self.bl_idname
        row2.operator('ar.delete_custom_icon', text="Delete", icon='TRASH')
        grid_flow = box.grid_flow(row_major=True, columns=35,
                                  even_columns=True, even_rows=True, align=True)
        custom_icon_values = [
            icon.icon_id for icon in preview_collections['ar_custom'].values()]
        for i, ic in enumerate(list(preview_collections['ar_custom'])):
            human_name = ic.lower().replace("_", " ")
            if self.search == '' or self.search.lower() in human_name:
                grid_flow.operator('ar.icon_selector', text="",
                                   icon_value=custom_icon_values[i]).icon = custom_icon_values[i]

    def check(self, context):
        return True


class AR_OT_icon_selector(Operator):
    bl_idname = "ar.icon_selector"
    bl_label = "Icon"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Select the Icon"

    icon: IntProperty(default=0)  # Icon: NONE

    def execute(self, context):
        ActRec_pref = get_preferences(context)
        ActRec_pref.selected_icon = self.icon
        return {"FINISHED"}


class AR_OT_add_custom_icon(Operator, ImportHelper):
    bl_idname = "ar.add_custom_icon"
    bl_label = "Add Custom Icon"
    bl_description = "Adds a custom Icon"

    filter_image: BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    activate_pop_up: StringProperty(default="")

    def execute(self, context):
        ActRec_pref = get_preferences(context)
        # supported blender image formats https://docs.blender.org/manual/en/latest/files/media/image_formats.html
        if os.path.isfile(self.filepath) and self.filepath.lower().endswith(tuple(bpy.path.extensions_image)):
            load_icon(ActRec_pref, self.filepath)
        else:
            self.report(
                {'ERROR'}, 'The selected File is not an Image or an Image Format supported by Blender')
        if self.activate_pop_up != "":
            exec("bpy.ops.%s%s" % (".".join(self.activate_pop_up.split(
                "_OT_")).lower(), "('INVOKE_DEFAULT', reuse= True)"))
        return {"FINISHED"}

    def cancel(self, context):
        if self.activate_pop_up != "":
            exec("bpy.ops.%s%s" % (".".join(self.activate_pop_up.split(
                "_OT_")).lower(), "('INVOKE_DEFAULT', reuse= True)"))
        super().cancel(context)


class AR_OT_delete_custom_icon(Operator):
    bl_idname = "ar.delete_custom_icon"
    bl_label = "Delete Icon"
    bl_description = "Delete a custom Icon"

    def get_select_all(self):
        return self.get("select_all", False)

    def set_select_all(self, value):
        self["select_all"] = value
        for icon in self.icons:
            icon["select_all"] = value

    class AR_icon(PropertyGroup):
        def get_selected(self):
            return self.get("selected", False) or self.get("select_all", False)

        def set_selected(self, value):
            if not self.get("select_all", False):
                self["selected"] = value

        icon_id: IntProperty()
        icon_name: StringProperty()
        selected: BoolProperty(default=False, name='Select', get=get_selected, set=set_selected)
    icons: CollectionProperty(type=AR_icon)
    select_all: BoolProperty(
        name="All Icons", description="Select all Icons", get=get_select_all, set=set_select_all)

    @classmethod
    def poll(cls, context):
        return len(preview_collections['ar_custom'])

    def invoke(self, context, event):
        coll = self.icons
        coll.clear()
        icon_list = list(preview_collections['ar_custom'])
        icon_list_values = [
            icon.icon_id for icon in preview_collections['ar_custom'].values()]
        for i in range(len(icon_list)):
            new = coll.add()
            new.icon_id = icon_list_values[i]
            new.icon_name = icon_list[i]
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        ActRec_pref = get_preferences(context)
        for ele in self.icons:
            if ele.selected or self.select_all:
                icon_path = ele.icon_name[3:]
                filenames = os.listdir(ActRec_pref.icon_path)
                names = [os.path.splitext(os.path.basename(path))[
                    0] for path in filenames]
                if icon_path in names:
                    os.remove(os.path.join(ActRec_pref.icon_path,
                              filenames[names.index(icon_path)]))
                unregister_icon(
                    preview_collections['ar_custom'], ele.icon_name)
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'select_all')
        box = layout.box()
        coll = self.icons
        for ele in coll:
            row = box.row()
            row.prop(ele, 'selected', text='')
            row.label(text=ele.icon_name[3:], icon_value=ele.icon_id)
# endregion


classes = [
    AR_OT_icon_selector,
    AR_OT_add_custom_icon,
    AR_OT_delete_custom_icon.AR_icon,
    AR_OT_delete_custom_icon
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    preview_collections['ar_custom'] = bpy.utils.previews.new()


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    for preview_collection in preview_collections.values():
        bpy.utils.previews.remove(preview_collection)
    preview_collections.clear()
# endregion
