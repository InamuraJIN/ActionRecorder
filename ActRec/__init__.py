from . import actrec

bl_info = {
    "name": "ActionRecorder",
    "author": "InamuraJIN, RivinHD",
    "version": (4, 0, 8),
    "blender": (3, 3, 5),
    "location": "View 3D",
    "warning": "",
    "docs_url": 'https://github.com/InamuraJIN/ActionRecorder/blob/master/README.md',  # Documentation
    "tracker_url": 'https://inamurajin.wixsite.com/website/post/bug-report',  # Report Bug
    "link": 'https://twitter.com/Inamura_JIN',
    "category": "System"
}


def register():
    actrec.register()


def unregister():
    actrec.unregister()
