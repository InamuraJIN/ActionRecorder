# region Registration
def register():
    from .locals import register as reg
    reg()
    from .categories import register as reg
    reg()


def unregister():
    from .locals import unregister as unreg
    unreg()
    from .categories import unregister as unreg
    unreg()
# endregion
