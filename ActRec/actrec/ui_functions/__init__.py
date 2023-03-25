"""no imports from other intra-modules
used by intra-modules: functions, operators"""

from .categories import (
    register_category,
    unregister_category,
    category_visible,
    get_visible_categories
)

from .globals import (
    draw_global_action,
    draw_simple_global_action
)


# region Registration
def unregister():
    from .categories import unregister as unreg
    unreg()
# endregion
