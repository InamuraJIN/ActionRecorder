import pytest
from ActRec.actrec.functions import shared
import bpy
import helper


@pytest.mark.parametrize(
    "check_list, name, output",
    [
        ([], "test", "test"),
        (["test"], "test", "test.001"),
        (["test", "test.001"], "test", "test.002"),
        (["test", "test.001", "test.002"], "test", "test.003"),
        (["test", "Ho", "something", "this", "there"], "name", "name"),
        ([], "", ""),
        ([""], "name", "name")
    ]
)
def test_check_for_duplicates(check_list, name, output):
    assert shared.check_for_duplicates(check_list, name) == output


@pytest.fixture(scope="function")
def clear_load_global(request):
    pref = shared.get_preferences(bpy.context)
    pref.global_actions.clear()
    helper.load_global_actions_test_data(pref)
    return helper.get_pref_data(request.param)


@pytest.mark.parametrize(
    "clear_load_global, exclude, output",
    [
        ('global_actions["c7a1f271164611eca91770c94ef23b30"].macros["c7a3dcba164611ecaaec70c94ef23b30"]', [],
         {
            "name": "c7a3dcba164611ecaaec70c94ef23b30",
            "id": "c7a3dcba164611ecaaec70c94ef23b30",
            "label": "Delete",
            "command": "bpy.ops.object.delete(use_global=False)",
            "active": True,
            "icon": 0,
            "icon_name": "NONE",
            "is_available": True,
            "ui_type": "",
            "alert": False,
            "operator_execution_context": "EXEC_DEFAULT"
        }),
        ('global_actions["c7a40353164611ecbaad70c94ef23b30"]',
         ["name", "selected", "alert", "macros.name", "macros.is_available", "macros.alert"],
         {
             "id": "c7a40353164611ecbaad70c94ef23b30",
             "label": "Subd Smooth",
             "macros": [
                 {
                     "id": "c7a40354164611ecb05c70c94ef23b30",
                     "label": "Subdivision Set",
                     "command": "bpy.ops.object.subdivision_set(level=1, relative=False)",
                     "active": True,
                     "icon": 0,
                     "icon_name": "NONE",
                     "ui_type": "",
                     "operator_execution_context": "EXEC_DEFAULT"
                 },
                 {
                     "id": "c7a40355164611ecb9cd70c94ef23b30",
                     "label": "Shade Smooth",
                     "command": "bpy.ops.object.shade_smooth()",
                     "active": True,
                     "icon": 0,
                     "icon_name": "NONE",
                     "ui_type": "",
                     "operator_execution_context": "EXEC_DEFAULT"
                 },
                 {
                     "id": "c7a42aa4164611ecba6570c94ef23b30",
                     "label": "Auto Smooth = True",
                     "command": "bpy.context.object.data.use_auto_smooth = True",
                     "active": True,
                     "icon": 0,
                     "icon_name": "NONE",
                     "ui_type": "",
                     "operator_execution_context": "EXEC_DEFAULT"
                 },
                 {
                     "id": "c7a6be1e164611ec8ede70c94ef23b30",
                     "label": "Auto Smooth Angle = 3.14159",
                     "command": "bpy.context.object.data.auto_smooth_angle = 3.14159",
                     "active": True,
                     "icon": 0,
                     "icon_name": "NONE",
                     "ui_type": "",
                     "operator_execution_context": "EXEC_DEFAULT"
                 }
             ],
             "icon": 127,
             "icon_name": "NODE_MATERIAL",
             "execution_mode": "GROUP",
             "description": "Play this Action Button"
         })],
    indirect=["clear_load_global"]
)
def test_property_to_python(clear_load_global, exclude, output):
    data = shared.property_to_python(clear_load_global, exclude)
    assert data == output


@ pytest.fixture(scope="function")
def apply_data(request):
    pref = shared.get_preferences(bpy.context)
    pref.global_actions.clear()
    helper.load_global_actions_test_data(pref)
    if request.param == 'global_actions["c7a1f271164611eca91770c94ef23b30"]':
        pref.global_actions["c7a1f271164611eca91770c94ef23b30"].macros.clear()
    return helper.get_pref_data(request.param)


@ pytest.mark.parametrize(
    "apply_data, data",
    [('global_actions["c7a1f271164611eca91770c94ef23b30"].macros["c7a3dcba164611ecaaec70c94ef23b30"]',
      {"id": "c7a3dcba164611ecaaec70c94ef23b30", "label": "Something",
       "command": "bpy.ops.object.delete(use_global=False)", "active": False, "icon": 15, "ui_type": ""}),
     ('global_actions["c7a1f271164611eca91770c94ef23b30"]',
      {"id": "c7a1f271164611eca91770c94ef23b30", "label": "Something",
       "macros":
       [{"id": "c7a3dcba164611ecaaec70c94ef23b30", "label": "Delete",
         "command": "bpy.ops.object.delete(use_global=False)", "active": False, "icon": 26, "ui_type": ""}],
       "icon": 7})],
    indirect=["apply_data"]
)
def test_apply_data_to_item(apply_data, data):
    shared.apply_data_to_item(apply_data, data)
    assert helper.compare_with_dict(apply_data, data)


@ pytest.mark.parametrize("collection, data",
                          [(bpy.context.preferences.addons['cycles'].preferences.devices,
                           {'name': "test", 'id': "TT", 'use': False, 'type': "OPTIX"})]
                          )
def test_add_data_to_collection(collection, data):
    length = len(collection)
    name = data['name']
    shared.add_data_to_collection(collection, data)
    index = collection.find(name)
    assert length + 1 == len(collection)
    assert index != -1
    assert helper.compare_with_dict(collection[name], data)
    collection.remove(index)


@pytest.mark.parametrize(
    "clear_load_global, index, data",
    [
        ('global_actions["c7a1f271164611eca91770c94ef23b30"].macros', 0,
         {
             "id": "c7a759ec164611ecb07c70c94ef23b30",
             "label": "Toggle Edit Mode",
             "command": "bpy.ops.object.editmode_toggle()",
             "active": True,
             "icon": 0,
             "ui_type": ""
         }
         ),
        ("global_actions", 1,
         {
             "id": "c7a759ee164611ecb84c70c94ef23b30",
             "label": "Merge",
             "macros": [
                 {
                     "id": "c7a759ef164611eca84970c94ef23b30",
                     "label": "Resize",
                     "command": "bpy.ops.transform.resize(value=(0, 0, 0))",
                     "active": True,
                     "icon": 0,
                     "ui_type": ""
                 },
                 {
                     "id": "c7a759f0164611ec84fd70c94ef23b30",
                     "label": "Merge by Distance",
                     "command": "bpy.ops.mesh.remove_doubles()",
                     "active": True,
                     "icon": 0,
                     "ui_type": ""
                 }
             ],
             "icon": 608
         })
    ],
    indirect=["clear_load_global"]
)
def test_insert_to_collection(clear_load_global, index, data):
    shared.insert_to_collection(clear_load_global, index, data)
    if index >= len(clear_load_global):
        index = len(clear_load_global) - 1
    assert helper.compare_with_dict(clear_load_global[index], data)


@pytest.mark.parametrize(
    "clear_load_global, index1, index2, output1, output2",
    [("global_actions", 0, 0,
      {
          "id": "c7a1f271164611eca91770c94ef23b30",
          "label": "Delete",
          "macros": [
              {
                  "id": "c7a3dcba164611ecaaec70c94ef23b30",
                  "label": "Delete",
                  "command": "bpy.ops.object.delete(use_global=False)",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              }
          ],
          "icon": 3
      },
      {
          "id": "c7a1f271164611eca91770c94ef23b30",
          "label": "Delete",
          "macros": [
              {
                  "id": "c7a3dcba164611ecaaec70c94ef23b30",
                  "label": "Delete",
                  "command": "bpy.ops.object.delete(use_global=False)",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              }
          ],
          "icon": 3
      }),
     ("global_actions", 0, 2,
      {
          "id": "c7a6be1f164611ec9a5570c94ef23b30",
          "label": "Align_X",
          "macros": [
              {
                  "id": "c7a6e499164611ec927970c94ef23b30",
                  "label": "Only Locations = True",
                  "command": "bpy.context.scene.tool_settings.use_transform_pivot_point_align = True",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              },
              {
                  "id": "c7a6e49a164611ec9f1370c94ef23b30",
                  "label": "Resize",
                  "command": "bpy.ops.transform.resize(value=(1, 0, 1))",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              },
              {
                  "id": "c7a6e49b164611ecadb070c94ef23b30",
                  "label": "Only Locations = False",
                  "command": "bpy.context.scene.tool_settings.use_transform_pivot_point_align = False",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              }
          ],
          "icon": 0
      },
      {
          "id": "c7a1f271164611eca91770c94ef23b30",
          "label": "Delete",
          "macros": [
              {
                  "id": "c7a3dcba164611ecaaec70c94ef23b30",
                  "label": "Delete",
                  "command": "bpy.ops.object.delete(use_global=False)",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              }
          ],
          "icon": 3
      }),
     ("global_actions", 0, 5,
      {
          "id": "c7a6be1f164611ec9a5570c94ef23b30",
          "label": "Align_X",
          "macros": [
              {
                  "id": "c7a6e499164611ec927970c94ef23b30",
                  "label": "Only Locations = True",
                  "command": "bpy.context.scene.tool_settings.use_transform_pivot_point_align = True",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              },
              {
                  "id": "c7a6e49a164611ec9f1370c94ef23b30",
                  "label": "Resize",
                  "command": "bpy.ops.transform.resize(value=(1, 0, 1))",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              },
              {
                  "id": "c7a6e49b164611ecadb070c94ef23b30",
                  "label": "Only Locations = False",
                  "command": "bpy.context.scene.tool_settings.use_transform_pivot_point_align = False",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              }
          ],
          "icon": 0
      },
      {
          "id": "c7a1f271164611eca91770c94ef23b30",
          "label": "Delete",
          "macros": [
              {
                  "id": "c7a3dcba164611ecaaec70c94ef23b30",
                  "label": "Delete",
                  "command": "bpy.ops.object.delete(use_global=False)",
                  "active": True,
                  "icon": 0,
                  "ui_type": ""
              }
          ],
          "icon": 3
      })
     ],
    indirect=["clear_load_global"]
)
def test_swap_collection_items(clear_load_global, index1, index2, output1, output2):
    shared.swap_collection_items(clear_load_global, index1, index2)
    if index1 >= len(clear_load_global):
        index1 = len(clear_load_global) - 1
    if index2 >= len(clear_load_global):
        index2 = len(clear_load_global) - 1
    assert helper.compare_with_dict(clear_load_global[index1], output1)
    assert helper.compare_with_dict(clear_load_global[index2], output2)
