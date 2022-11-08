from .main import (
    ui_space_types,
    panel_factory,
)

# region Registration


def register():
    from .main import register as reg
    reg()


def unregister():
    from .main import unregister as unreg
    unreg()
# endregion
