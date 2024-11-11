from . import actrec

bl_info = {
    "name": "ActionRecorder",
    "author": "InamuraJIN, RivinHD",
    "version": (4, 2, 0),
    "blender": (4, 2, 0),
    "location": "View 3D",
    "warning": "",
    "docs_url": 'https://inamurajin.github.io/ActionRecorder/',  # Documentation
    "tracker_url": 'https://inamurajin.wixsite.com/website/post/bug-report',  # Report Bug
    "link": 'https://twitter.com/Inamura_JIN',
    "category": "System"
}


def register():
    actrec.register()


def unregister():
    actrec.unregister()
