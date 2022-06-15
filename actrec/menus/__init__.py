# region Registration
def register():
    from .locals import register as reg
    reg()

def unregister():
    from .locals import unregister as unreg
    unreg()
# endregion
