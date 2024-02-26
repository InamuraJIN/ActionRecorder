"""only relative import from intra-modules: functions, ui, properties"""

from .categories import (
    AR_OT_category_add,
    AR_OT_category_edit,
    AR_OT_category_interface,
    AR_OT_category_apply_visibility,
    AR_OT_category_delete_visibility,
    AR_OT_category_delete
)

from .globals import (
    AR_OT_global_recategorize_action,
    AR_OT_global_import,
    AR_OT_global_import_settings
)

from .locals import (
    AR_OT_local_to_global
)

from .helper import (
    AR_OT_helper_object_to_collection
)

from .preferences import (
    AR_OT_preferences_directory_selector,
    AR_OT_preferences_recover_directory
)

from .shared import (
    AR_OT_check_ctrl
)

# region Registration


def register():
    from .categories import register as reg
    reg()
    from .globals import register as reg
    reg()
    from .locals import register as reg
    reg()
    from .macros import register as reg
    reg()
    from .helper import register as reg
    reg()
    from .preferences import register as reg
    reg()
    from .shared import register as reg
    reg()


def unregister():
    from .categories import unregister as unreg
    unreg()
    from .globals import unregister as unreg
    unreg()
    from .locals import unregister as unreg
    unreg()
    from .macros import unregister as unreg
    unreg()
    from .helper import unregister as unreg
    unreg()
    from .preferences import unregister as unreg
    unreg()
    from .shared import unregister as unreg
    unreg()
# endregion
