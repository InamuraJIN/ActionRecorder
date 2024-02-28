# region Imports
# external modules
from typing import Optional, TYPE_CHECKING


# blender modules
from bpy.types import AddonPreferences

# relative imports
if TYPE_CHECKING:
    from ..preferences import AR_preferences
else:
    AR_preferences = AddonPreferences
# endregion


# region functions


def get_category_id(ActRec_pref: AR_preferences, id: str, index: int) -> str:
    """
    get category id based on id (check for existence) or index
    fallback to selected category if no match occurred

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        id (str): id to check
        index (int): index of the category

    Returns:
        str: id of the category, fallback to selected category if not found
    """
    if ActRec_pref.categories.find(id) != -1:
        return id

    if index >= 0 and len(ActRec_pref.categories) > index:
        return ActRec_pref.categories[index].id
    else:
        return ActRec_pref.selected_category


def read_category_visibility(ActRec_pref: AR_preferences, id: str) -> Optional[list]:
    """
    get all areas and modes where the category with the given id is visible

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        id (str): id of the category

    Returns:
        Optional[list]: dict on success, None on fail
    """
    visibility = []
    category = ActRec_pref.categories.get(id, None)
    if not category:
        return
    for area in category.areas:
        for mode in area.modes:
            visibility.append((area.type, mode.type))
        if len(area.modes) == 0:
            visibility.append((area.type, 'all'))
    return visibility
# endregion
