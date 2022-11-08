from .locals import (
    AR_UL_locals
)

from .macros import (
    AR_UL_macros
)

# region Registration


def register():
    from .locals import register as reg
    reg()
    from .macros import register as reg
    reg()


def unregister():
    from .locals import unregister as unreg
    unreg()
    from .macros import unregister as unreg
    unreg()
# endregion
