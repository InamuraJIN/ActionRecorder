"""used by intra-modules: preferences, operators"""

from .categories import (
    AR_category
)

from .globals import (
    AR_global_actions,
    AR_global_import_category,
    AR_global_export_categories
)

from .locals import (
    AR_local_actions,
    AR_local_load_text
)

from .macros import (
    AR_macro_multiline,
    AR_event_object_name
)

from .shared import (
    Id_based,
    AR_macro,
    AR_action,
    AR_scene_data
)

# region Registration


def register():
    from .shared import register as reg
    reg()
    from .categories import register as reg
    reg()
    from .globals import register as reg
    reg()
    from .locals import register as reg
    reg()
    from .macros import register as reg
    reg()


def unregister():
    from .shared import unregister as unreg
    unreg()
    from .categories import unregister as unreg
    unreg()
    from .globals import unregister as unreg
    unreg()
    from .locals import unregister as unreg
    unreg()
    from .macros import unregister as unreg
    unreg()
# endregion
