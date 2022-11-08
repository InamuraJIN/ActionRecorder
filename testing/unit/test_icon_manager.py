import pytest
from ActRec.actrec import icon_manager
import os
import bpy
from ActRec.actrec.functions.shared import get_preferences

"""
@pytest.mark.parametrize(
    ("input, output",
        [
            (212, 212),
            ("sefsfse", 101),
            (None, 101),
            ("TRASH", 21)
        ]
     )
)"""


def test_get_icons_values():
    assert 0 not in icon_manager.get_icons_values()


def test_get_icons_names():
    assert 'NONE' not in icon_manager.get_icons_names()


@pytest.mark.parametrize(
    "file, name, only_new, success",
    [
        ("test_icon_png1.png", "AR_test_icon_png1", False, True),
        ("test_icon_png2.png", "AR_test_icon_png2", False, True),
        ("test_icon_jpg.jpg", "AR_test_icon_jpg", False, True),
        ("test_icon_png1.png", "AR_test_icon_png1.001", False, True),
        ("test_icon_jpg.jpg", "AR_test_icon_jpg", True, True)
    ]
)
def test_load_icon(file, name, only_new, success):
    # include register_icon testing
    # don't know why preview couldn't be registered, therefore manual
    dirpath = "test_src_data\\icon_manager"
    path = os.path.join(os.path.dirname(__file__), dirpath, file)
    pref = get_preferences(bpy.context)
    pref.icon_path = os.path.dirname(__file__)
    icon_manager.load_icon(pref, path, only_new)
    assert (name in list(icon_manager.preview_collections['ar_custom'])) == success


if __name__ == "__main__":
    pytest.main()
