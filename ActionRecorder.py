# region Imports
import bpy
from bpy.app.handlers import persistent
import os
import shutil
import json
from json.decoder import JSONDecodeError
import zipfile
import time
import webbrowser
from addon_utils import check, paths, enable
from .config import config
import atexit
from urllib import request
from io import BytesIO
from . import __init__ as init
import base64
import random
import math
import inspect
import functools
import numpy as np
import copy
from importlib import reload
from .Category import Category as CatVisibility
import queue

from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import Panel, UIList, Operator, PropertyGroup, AddonPreferences, Menu
from bpy_extras.io_utils import ImportHelper, ExportHelper
import rna_keymap_ui
import bpy.utils.previews

import sys
# endregion

# region Variables
classes = []
classespanel = []
categoriesclasses = []
catlength = [0]
ontempload = [False]
multiselection_buttons = [False, True]
oninit = [False]
preview_collections = {}
catVisPath = os.path.join(os.path.dirname(__file__), "Category.py")
execution_queue = queue.Queue()

class Data:
    Edit_Command = None
    Record_Edit_Index = None
    Commands_RenderComplete = []
    Commands_RenderInit = []
    CatVisis = []
    alert_index = None
    activeareas = []
    ActiveTimers = 0
# endregion

# region UIList
class AR_UL_Selector(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        self.use_filter_show = False
        self.use_filter_sort_lock = True
        row = layout.row(align= True)
        row.alert = item.alert
        row.operator(AR_OT_Record_Icon.bl_idname, text= "", icon_value= AR_Var.Record_Coll[0].Command[index].icon, emboss= False).index = index
        col = row.column()
        col.ui_units_x = 0.5
        row.prop(item, 'cname', text = '', emboss= False)
classes.append(AR_UL_Selector)
class AR_UL_Command(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        self.use_filter_show = False
        self.use_filter_sort_lock = True
        row = layout.row(align= True)
        row.alert = item.alert
        row.prop(item, 'active', text= "")
        row.operator(AR_OT_Command_Edit.bl_idname, text= item.macro, emboss= False).index = index
classes.append(AR_UL_Command)
# endregion

# region Functions
def CheckCommand(num): #Add a new Collection if necessary
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if len(AR_Var.Record_Coll) <= num:
        AR_Var.Record_Coll.add()
    return num

def Get_Recent(Return_Bool):
    #remove other Recent Reports
    reports = \
    [
    bpy.data.texts.remove(t)
    for t in bpy.data.texts
        if t.name.startswith('Recent Reports')
    ]
    # make a report
    win = bpy.context.window_manager.windows[0]
    area = win.screen.areas[0]
    area_type = area.type
    area.type = 'INFO'
    override = bpy.context.copy()
    override['window'] = win
    override['screen'] = win.screen
    override['area'] = win.screen.areas[0]
    bpy.ops.info.select_all(override, action='SELECT')
    bpy.ops.info.report_copy(override)
    area.type = area_type
    clipboard = bpy.context.window_manager.clipboard
    bpy.data.texts.new('Recent Reports')
    bpy.data.texts['Recent Reports'].write(clipboard)
    # print the report
    if Return_Bool == 'Reports_All':
        return bpy.data.texts['Recent Reports'].lines
    elif Return_Bool == 'Reports_Length':
        return len(bpy.data.texts['Recent Reports'].lines)

def GetMacro(name):
    if name.startswith("bpy.ops"):
        try:
            return eval(name.split("(")[0] + ".get_rna_type().name")
        except:
            return name
    elif name.startswith('bpy.data.window_managers["WinMan"].(null)'):
        return True
    elif name.startswith('bpy.context'):
        split = name.split('=')
        if len(split) > 1:
            return split[0].split('.')[-1] + " = " + split[1]
        else:
            return ".".join(split[0].split('.')[-2:])
    else:
        return None

def Record(Num, Mode):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    Recent = Get_Recent('Reports_All')
    if Mode == 'Start':
        AR_Prop.Record = True
        AR_Prop.Temp_Num = len(Recent)
        bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
    else:
        AR_Prop.Record = False
        notadded = []
        startCommand = ""
        lastCommand = ""
        for i in range(AR_Prop.Temp_Num, len(Recent)):
            TempText = Recent[i - 1].body
            if TempText.count('bpy'):
                name = TempText[TempText.find('bpy'):]
                if lastCommand.split("(", 1)[0] == name.split("(", 1)[0] and startCommand != name:
                    lastCommand = name
                    continue
                macro = GetMacro(name)
                if macro is True:
                    continue
                if startCommand != lastCommand:
                    lastMacro = GetMacro(lastCommand)
                    if lastMacro is None:
                        notadded.append(name)
                        if AR_Var.CreateEmpty:
                            Item = AR_Var.Record_Coll[CheckCommand(Num)].Command[-1]
                            Item.macro = "<Empty>"
                            Item.cname = ""
                    else:
                        Item = AR_Var.Record_Coll[CheckCommand(Num)].Command[-1]
                        Item.macro = lastMacro
                        Item.cname = lastCommand
                lastCommand = name
                startCommand = name
                if macro is None:
                    notadded.append(name)
                    if AR_Var.CreateEmpty:
                        Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                        Item.macro = "<Empty>"
                        Item.cname = ""
                else:
                    Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                    Item.macro = macro
                    Item.cname = name
        if startCommand != lastCommand:
            lastMacro = GetMacro(lastCommand)
            if lastMacro is None:
                notadded.append(name)
                if AR_Var.CreateEmpty:
                    Item = AR_Var.Record_Coll[CheckCommand(Num)].Command[-1]
                    Item.macro = "<Empty>"
                    Item.cname = ""
            else:
                Item = AR_Var.Record_Coll[CheckCommand(Num)].Command[-1]
                Item.macro = lastMacro
                Item.cname = lastCommand
        UpdateRecordText(Num)
        bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
        return notadded

def CreateTempFile():
    tpath = bpy.app.tempdir + "temp.json"
    if not os.path.exists(tpath):
        print(tpath)
        with open(tpath, 'w', encoding='utf8') as tempfile:
            json.dump({"0":[]}, tempfile)
    return tpath

def TempSave(Num):  # write new command to temp.json file
    tpath = CreateTempFile()
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    with open(tpath, 'r+', encoding='utf8') as tempfile:   
        data = json.load(tempfile)
        data.update({str(Num):[]})
        data["0"] = [{"name": i.cname, "macro": i.macro, "icon": i.icon, "active": i.active} for i in AR_Var.Record_Coll[CheckCommand(0)].Command]
        tempfile.truncate(0)
        tempfile.seek(0)
        json.dump(data, tempfile)

def TempUpdate(): # update all commands in temp.json file
    tpath = CreateTempFile()
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    with open(tpath, 'r+', encoding='utf8') as tempfile:
        tempfile.truncate(0)    
        tempfile.seek(0)
        data = {}
        for cmd in range(len(AR_Var.Record_Coll[CheckCommand(0)].Command) + 1):
            data.update({str(cmd):[{"name": i.cname, "macro": i.macro, "icon": i.icon, "active": i.active} for i in AR_Var.Record_Coll[CheckCommand(cmd)].Command]})
        json.dump(data, tempfile)

def TempUpdateCommand(Key): # update one command in temp.json file
    tpath = CreateTempFile()
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    with open(tpath, 'r+', encoding='utf8') as tempfile:
        data = json.load(tempfile)
        data[str(Key)] = [{"name": i.cname, "macro": i.macro, "icon": i.icon, "active": i.active} for i in AR_Var.Record_Coll[CheckCommand(int(Key))].Command]
        tempfile.truncate(0)
        tempfile.seek(0)
        json.dump(data, tempfile)

@persistent
def TempLoad(dummy): # load commands after undo
    tpath = bpy.app.tempdir + "temp.json"
    ontempload[0] = True
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if os.path.exists(tpath):
        with open(tpath, 'r', encoding='utf8') as tempfile:
            data = json.load(tempfile)
        command = AR_Var.Record_Coll[CheckCommand(0)].Command
        command.clear()
        keys = list(data.keys())
        for i in range(1, len(data)):
            Item = command.add()
            Item.macro = data["0"][i - 1]["macro"]
            Item.cname = data["0"][i - 1]["name"]
            Item.icon = data["0"][i - 1]["icon"]
            record = AR_Var.Record_Coll[CheckCommand(i)].Command
            record.clear()
            for j in range(len(data[keys[i]])):
                Item = record.add()
                Item.macro = data[keys[i]][j]["macro"]
                Item.cname = data[keys[i]][j]["name"]
                Item.icon = data[keys[i]][j]["icon"]
                Item.active = data[keys[i]][j]["active"]
    ontempload[0] = False

def getlastoperation(data, i=-1):
    if len(data) < 1:
        return ("", i)
    if data[i].body.startswith("bpy."):
        return (data[i].body, i)
    else:
        return getlastoperation(data, i-1)

def CheckAddCommand(data, line = 0):
    name, index = getlastoperation(data)
    macro = GetMacro(name)
    if macro is True:
        return CheckAddCommand(data[ :index], line + 1)
    else:
        return (name, macro, len(data) + line - 1)

def Add(Num, command = None):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if Num:
        Recent = Get_Recent('Reports_All')
        try: #Add Macro
            if command is None:
                name, macro, line = CheckAddCommand(Recent)
            else:
                name = command
                macro = GetMacro(command)
                line = -1
            notadded = False
            if macro is None or macro is True:
                notadded = name
                if macro is None and AR_Var.CreateEmpty:
                    Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                    Item.macro = "<Empty>"
                    Item.cname = ""
            elif AR_Var.LastLineIndex == line and AR_Var.LastLineCmd == name:
                notadded = "<Empty>"
                Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                Item.macro = "<Empty>"
                Item.cname = ""
            else:
                Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                Item.macro = macro
                Item.cname = name
                if line != -1:
                    AR_Var.LastLine = macro
                    AR_Var.LastLineIndex = line
                    AR_Var.LastLineCmd = name
            UpdateRecordText(Num)
            bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
            return notadded
        except Exception as err:
            if AR_Var.CreateEmpty:
                Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                Item.macro = "<Empty>"
                Item.cname = ""
            print("Action Adding Failure: " + str(err))
            bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
            return True
    else: # Add Record
        Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
        if command == None:
            Item.cname = CheckForDublicates([cmd.cname for cmd in AR_Var.Record_Coll[CheckCommand(0)].Command], 'Untitled.001')
        else:
            Item.cname = CheckForDublicates([cmd.cname for cmd in AR_Var.Record_Coll[CheckCommand(0)].Command], command)
    AR_Var.Record_Coll[CheckCommand(Num)].Index = len(AR_Var.Record_Coll[CheckCommand(Num)].Command) - 1
    bpy.data.texts.new(Item.cname)

def UpdateRecordText(Num):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    RecName = AR_Var.Record_Coll[CheckCommand(0)].Command[Num - 1].cname
    if bpy.data.texts.find(RecName) == -1:
        bpy.data.texts.new(RecName)
    bpy.data.texts[RecName].clear()
    bpy.data.texts[RecName].write("".join([cmd.cname + "\n" for cmd in AR_Var.Record_Coll[CheckCommand(Num)].Command]))

def Remove(Num): # Remove Record or Macro
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    index = AR_Var.Record_Coll[CheckCommand(Num)].Index
    if Num:
        UpdateRecordText(Num)
    else:
        txtname = AR_Var.Record_Coll[CheckCommand(Num)].Command[index].cname
        if bpy.data.texts.find(txtname) != -1:
            bpy.data.texts.remove(bpy.data.texts[txtname])
    AR_Var.Record_Coll[Num].Command.remove(index)
    if not Num:
        AR_Var.Record_Coll.remove(index + 1)
    AR_Var.Record_Coll[Num].Index = (index - 1) * (index - 1 > 0)

def Move(Num , Mode) :# Move Record or Macro
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    index1 = AR_Var.Record_Coll[CheckCommand(Num)].Index
    if Mode == 'Up' :
        index2 = AR_Var.Record_Coll[CheckCommand(Num)].Index - 1
    else :
        index2 = AR_Var.Record_Coll[CheckCommand(Num)].Index + 1
    LengthTemp = len(AR_Var.Record_Coll[CheckCommand(Num)].Command)
    if (2 <= LengthTemp) and (0 <= index1 < LengthTemp) and (0 <= index2 < LengthTemp):
        AR_Var.Record_Coll[CheckCommand(Num)].Command.move(index1, index2)
        AR_Var.Record_Coll[CheckCommand(Num)].Index = index2
        if not Num:
            AR_Var.Record_Coll.move(index1 + 1, index2 + 1)

def Select_Command(Mode): # Select the upper/lower Record
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    currentIndex = AR_Var.Record_Coll[CheckCommand(0)].Index
    listlen = len(AR_Var.Record_Coll[CheckCommand(0)].Command) - 1
    if Mode == 'Up':
        if currentIndex == 0:
            AR_Var.Record_Coll[CheckCommand(0)].Index = listlen
        else:
            AR_Var.Record_Coll[CheckCommand(0)].Index = currentIndex - 1
    else:
        if currentIndex == listlen:
            AR_Var.Record_Coll[CheckCommand(0)].Index = 0
        else:
            AR_Var.Record_Coll[CheckCommand(0)].Index = currentIndex + 1

def RespAlert(Command, index, CommandIndex):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if CommandIndex == AR_Var.Record_Coll[CheckCommand(index + 1)].Index:
        if AR_Var.Record_Coll[CheckCommand(index + 1)].Index == 0:
            if len(AR_Var.Record_Coll[CheckCommand(index + 1)].Command) > 1:
                AR_Var.Record_Coll[CheckCommand(index + 1)].Index = 1
                bpy.context.area.tag_redraw()
        else:
            AR_Var.Record_Coll[CheckCommand(index + 1)].Index = 0
            bpy.context.area.tag_redraw()
        bpy.app.timers.register(functools.partial(AfterAlert, Command, index, CommandIndex), first_interval= 0.01)
    else:
        AfterAlert(Command, index, CommandIndex)
    return True

def AfterAlert(Command, index, CommandIndex):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Record_Coll[CheckCommand(index + 1)].Index = CommandIndex
    Command.alert = True
    AR_Var.Record_Coll[CheckCommand(index + 1)].Index = CommandIndex
    Alert(index)

def Play(Commands, index, AllLoops = None, extension = 0 ): #Execute the Macro
    if AllLoops is None:
        AllLoops = getAllLoops(Commands)
    for i, Command in enumerate(Commands):
        if Command.active:
            split = Command.cname.split(":")
            if split[0] == 'ar.event':
                data = json.loads(":".join(split[1:]))
                if data['Type'] == 'Timer':
                    bpy.app.timers.register(functools.partial(TimerCommads, Commands[i + 1:], index), first_interval = data['Time'])
                    Data.ActiveTimers += 1
                    bpy.ops.ar.command_run_queued('INVOKE_DEFAULT')
                    return
                elif data['Type'] == 'Loop' :
                    loopi = getIndexInLoop(i + extension, AllLoops, 'Loop')
                    if loopi == None:
                        continue
                    else:
                        AllLoops[loopi].pop('Loop', None)
                    if data['StatementType'] == 'python':
                        try:
                            while eval(data["PyStatement"]):
                                BackLoops = Play(Commands[int(i) + 1:], index, copy.deepcopy(AllLoops), extension + 2)
                                if BackLoops == True:
                                    return True
                            else:
                                AllLoops = BackLoops
                            continue
                        except:
                            return RespAlert(Command, index, i)
                        return
                    else:
                        for k in np.arange(data["Startnumber"], data["Endnumber"], data["Stepnumber"]):
                            BackLoops = Play(Commands[int(i) + 1:], index, copy.deepcopy(AllLoops), extension + 2)
                            if BackLoops == True:
                                return True
                        else:
                            AllLoops = BackLoops    
                        AllLoops[loopi].pop('End', None)
                        continue
                elif data['Type'] == 'EndLoop':
                    loopi = getIndexInLoop(i + extension, AllLoops, 'End')
                    if loopi == None:
                        continue
                    else:
                        if 'Loop' not in AllLoops[loopi]:
                            return AllLoops
                elif data['Type'] == 'Render Complet':
                    Data.Commands_RenderComplete.append((index, Commands[i + 1:]))
                    return
                elif data['Type'] == 'Render Init':
                    Data.Commands_RenderInit.append((index ,Commands[i + 1:]))
                    return
                elif data['Type'] == 'Select Object':
                    obj = bpy.data.objects[data['Object']]
                    objs = bpy.context.view_layer.objects
                    if obj in [o for o in objs]:
                        objs.active = obj
                    else:
                        return RespAlert(Command, index, i)
                    continue
                elif data['Type'] == 'Select Vertices':
                    obj = bpy.context.object
                    mode = bpy.context.active_object.mode
                    bpy.ops.object.mode_set(mode = 'EDIT') 
                    bpy.ops.mesh.select_mode(type="VERT")
                    bpy.ops.mesh.select_all(action = 'DESELECT')
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                    mesh = bpy.context.object.data
                    objverts = mesh.vertices
                    verts = data['Verts']
                    if max(verts) < len(objverts):
                        for vert in objverts:
                            vert.select = False
                        for i in verts:
                            objverts[i].select = True
                        mesh.update()
                    else:
                        bpy.ops.object.mode_set(mode=mode)
                        return RespAlert(Command, index, i)
                    bpy.ops.object.mode_set(mode=mode)
                    continue
                else:
                    return RespAlert(Command, index, i)
            try:
                exec(Command.cname)
            except Exception as err:
                print(err)
                return RespAlert(Command, index, i)

def Clear(Num) : # Clear all Macros
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Record_Coll[CheckCommand(Num)].Command.clear()
    UpdateRecordText(Num)

def Save(): #Save Buttons to Storage
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    for savedfolder in os.listdir(AR_Var.StorageFilePath):
        folderpath = os.path.join(AR_Var.StorageFilePath, savedfolder)
        for savedfile in os.listdir(folderpath):
            os.remove(os.path.join(folderpath, savedfile))
        os.rmdir(folderpath)
    for cat in AR_Var.Categories:
        panelpath = os.path.join(AR_Var.StorageFilePath, f"{GetPanelIndex(cat)}~" + cat.pn_name)
        os.mkdir(panelpath)
        start = cat.Instance_Start
        for cmd_i in range(start, start + cat.Instance_length):
            with open(os.path.join(panelpath, f"{cmd_i - start}~" + AR_Var.Instance_Coll[cmd_i].name + "~" + f"{AR_Var.Instance_Coll[cmd_i].icon}" + ".py"), 'w', encoding='utf8') as cmd_file:
                for cmd in AR_Var.Instance_Coll[cmd_i].command:
                    cmd_file.write(cmd.name + "\n")

def Load():#Load Buttons from Storage
    print('------------------Load-----------------')
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    for cat in AR_Var.Categories:
        RegisterUnregister_Category(GetPanelIndex(cat), False)
    AR_Var.Categories.clear()
    AR_Var.ar_enum.clear()
    AR_Var.Instance_Coll.clear()
    AR_Var.Instance_Index = 0
    for folder in os.listdir(AR_Var.StorageFilePath):
        folderpath = os.path.join(AR_Var.StorageFilePath, folder)
        if os.path.isdir(folderpath):
            textfiles = os.listdir(folderpath)
            new = AR_Var.Categories.add()
            name = "".join(folder.split('~')[1:])
            new.name = name
            new.pn_name = name
            new.Instance_Start = len(AR_Var.Instance_Coll)
            new.Instance_length = len(textfiles)
            sortedtxt = [None] * len(textfiles)
            RegisterUnregister_Category(GetPanelIndex(new))
            for i in textfiles:
                new_e = AR_Var.ar_enum.add()
                e_index = len(AR_Var.ar_enum) - 1
                new_e.name = str(e_index)
                new_e.Index = e_index
                new_e.Value = False
            for txt in textfiles:
                sortedtxt[int(txt.split('~')[0])] = txt #get the index 
            for i in range(len(sortedtxt)):
                txt = sortedtxt[i]
                inst = AR_Var.Instance_Coll.add()
                inst.name = "".join(txt.split('~')[1:-1])
                icon = os.path.splitext(txt)[0].split('~')[-1]
                if icon.isnumeric():
                    icon = int(icon)
                else:
                    iconlist = getIcons()
                    if icon in iconlist:
                        icon = getIconsvalues()[iconlist.index(icon)]
                    else:
                        icon = 101 # Icon: BLANK1
                inst.icon = icon
                CmdList = []
                with open(os.path.join(folderpath, txt), 'r', encoding='utf8') as text:
                    for line in text.readlines():
                        cmd = inst.command.add()
                        cmd.name = line.strip()
    for iconpath in os.listdir(AR_Var.IconFilePath): # Load Icons
        filepath = os.path.join(AR_Var.IconFilePath, iconpath)
        if os.path.isfile(filepath):
            LoadIcons(filepath)
    SetEnumIndex()

@persistent
def LoadLocalActions(dummy):
    print('-----------Load Local Actions-----------')
    scene = bpy.context.scene
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Record_Coll.clear()
    local = json.loads(scene.ar_local)
    for ele in local:
        loc = AR_Var.Record_Coll.add()
        loc.name = ele['name']
        loc.Index = ele['Index']
        loc.Command.clear()
        for cmd in ele['Command']:
            locmd = loc.Command.add()
            locmd.cname = cmd['cname']
            locmd.macro = cmd['macro']
            locmd.active = cmd['active']
            locmd.alert = cmd['alert']
            locmd.icon = cmd['icon']
    # Check Command
    i = 0
    while i < len(local):
        ele = local[i]
        loc = AR_Var.Record_Coll[i]
        if  loc.name == ele['name'] and loc.Index == ele['Index'] and len(ele['Command']) == len(loc.Command):
            i += 1
        else:
            AR_Var.Record_Coll.remove(i)
    SaveToDataHandler(None)

def Recorder_to_Instance(panel): #Convert Record to Button
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    i = panel.Instance_Start +  panel.Instance_length
    data = {"name":CheckForDublicates([AR_Var.Instance_Coll[j].name for j in range(panel.Instance_Start, i)], AR_Var.Record_Coll[CheckCommand(0)].Command[AR_Var.Record_Coll[CheckCommand(0)].Index].cname),
            "command": [Command.cname for Command in AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command],
            "icon": AR_Var.Record_Coll[CheckCommand(0)].Command[AR_Var.Record_Coll[CheckCommand(0)].Index].icon}
    Inst_Coll_Insert(i, data , AR_Var.Instance_Coll)
    panel.Instance_length += 1
    new_e = AR_Var.ar_enum.add()
    e_index = len(AR_Var.ar_enum) - 1
    new_e.name = str(e_index)
    new_e.Index = e_index
    p_i = GetPanelIndex(panel)
    categories = AR_Var.Categories
    if p_i < len(categories):
        for cat in categories[ p_i + 1: ]:
            cat.Instance_Start += 1

def Instance_to_Recorder():#Convert Button to Record
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    l = []
    if multiselection_buttons[0]:
        for i in range(len(AR_Var.ar_enum)):
            if AR_Var.ar_enum[i].Value:
                l.append(i)
    else:
        l.append(AR_Var.Instance_Index)
    for Index in l:
        Item = AR_Var.Record_Coll[CheckCommand(0)].Command.add()
        Item.cname = CheckForDublicates([cmd.cname for cmd in AR_Var.Record_Coll[CheckCommand(0)].Command], AR_Var.Instance_Coll[Index].name)
        Item.icon = AR_Var.Instance_Coll[Index].icon
        for Command in AR_Var.Instance_Coll[Index].command:
            Item = AR_Var.Record_Coll[CheckCommand(len(AR_Var.Record_Coll[CheckCommand(0)].Command))].Command.add()
            macro = GetMacro(Command.name)
            if macro == None:
                split = Command.name.split(":")
                if split[0] == "ar.event":
                    data = json.loads(":".join(split[1:]))
                    Item.macro = "Event:" + data['Type']
                else:
                    Item.macro = Command.name
            else: 
                Item.macro = macro   
            Item.cname = Command.name
        AR_Var.Record_Coll[CheckCommand(0)].Index = len(AR_Var.Record_Coll[CheckCommand(0)].Command) - 1
        UpdateRecordText(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)

def Execute_Instance(Num): #Execute a Button
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    for cmd in AR_Var.Instance_Coll[Num].command:
        try:
            exec(cmd.name)
        except:
            return True # Alert

def Rename_Instance(): #Rename a Button
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Instance_Coll[AR_Var.Instance_Index].name = AR_Var.Rename

def I_Remove(): # Remove a Button
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    l = []
    if multiselection_buttons[0]:
        for i in range(len(AR_Var.ar_enum)):
            if AR_Var.ar_enum[i].Value:
                l.append(i)
    else:
        l.append(AR_Var.Instance_Index)
    offset = 0
    for Index in l:
        if len(AR_Var.Instance_Coll) :
            Index = Index - offset
            AR_Var.Instance_Coll.remove(Index)
            AR_Var.ar_enum.remove(len(AR_Var.ar_enum) - 1)
            categories = AR_Var.Categories
            for cat in categories:
                if Index >= cat.Instance_Start and Index < cat.Instance_Start + cat.Instance_length:
                    cat.Instance_length -= 1
                    p_i = GetPanelIndex(cat)
                    if p_i < len(categories):
                        for cat in categories[ p_i + 1: ]:
                            cat.Instance_Start -= 1
                    break
            if len(AR_Var.Instance_Coll) and len(AR_Var.Instance_Coll)-1 < Index :
                AR_Var.Instance_Index = len(AR_Var.Instance_Coll)-1
            offset += 1
    SetEnumIndex()

def I_Move(Mode): # Move a Button to the upper/lower
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    l = []
    if multiselection_buttons[0]:
        multiselection_buttons[1] = False
        for i in range(len(AR_Var.ar_enum)):
            if AR_Var.ar_enum[i].Value:
                l.append(i)
    else:
        l.append(AR_Var.Instance_Index)
    if Mode == 'Down':
        l.reverse()
    for index1 in l:
        if Mode == 'Up' :
            index2 = index1 - 1
        else :
            index2 = index1 + 1
        LengthTemp = len(AR_Var.Instance_Coll)
        if (2 <= LengthTemp) and (0 <= index1 < LengthTemp) and (0 <= index2 <LengthTemp):
            AR_Var.Instance_Coll[index1].name , AR_Var.Instance_Coll[index2].name = AR_Var.Instance_Coll[index2].name , AR_Var.Instance_Coll[index1].name
            AR_Var.Instance_Coll[index1].icon , AR_Var.Instance_Coll[index2].icon = AR_Var.Instance_Coll[index2].icon , AR_Var.Instance_Coll[index1].icon
            index1cmd = [cmd.name for cmd in AR_Var.Instance_Coll[index1].command]
            index2cmd = [cmd.name for cmd in AR_Var.Instance_Coll[index2].command]
            AR_Var.Instance_Coll[index1].command.clear()
            AR_Var.Instance_Coll[index2].command.clear()
            for cmd in index2cmd:
                new = AR_Var.Instance_Coll[index1].command.add()
                new.name = cmd
            for cmd in index1cmd:
                new = AR_Var.Instance_Coll[index2].command.add()
                new.name = cmd
            AR_Var.ar_enum[index1].Value = False
            AR_Var.ar_enum[index2].Value = True
        else:
            break
    if multiselection_buttons[0]:
        multiselection_buttons[1] = True

#Initalize Standert Button List
@persistent
def InitSavedPanel(dummy = None):
    try:
        bpy.app.timers.unregister(TimerInitSavedPanel)
    except:
        if bpy.data.filepath == '':
            return
    try:
        bpy.app.handlers.depsgraph_update_pre.remove(InitSavedPanel)
    except:
        return
    oninit[0] = True
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if bpy.data.filepath == '':
        AR_Var.Record_Coll.clear()
    LoadLocalActions(None)
    AR_Var.Update = False
    AR_Var.Version = ''
    AR_Var.Restart = False
    if AR_Var.AutoUpdate:
        bpy.ops.ar.check_update('EXEC_DEFAULT')
    if not os.path.exists(AR_Var.StorageFilePath):
        os.mkdir(AR_Var.StorageFilePath)
    if not os.path.exists(AR_Var.IconFilePath):
        os.mkdir(AR_Var.IconFilePath)
    Load()
    catlength[0] = len(AR_Var.Categories)
    TempSaveCats()
    TempUpdate()
    multiselection_buttons[0] = False
    oninit[0] = False

def TimerInitSavedPanel():
    InitSavedPanel()

def GetPanelIndex(cat): #Get Index of a Category
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    return AR_Var.Categories.find(cat.name)

def SetEnumIndex(): #Set enum, if out of range to the first enum
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    if len(AR_Var.ar_enum):
        enumIndex = AR_Var.Instance_Index * (AR_Var.Instance_Index < len(AR_Var.ar_enum))
        AR_Var.ar_enum[enumIndex].Value = True
        AR_Var.Instance_Index = enumIndex  

def CreateTempCats(): #Creat temp file to save categories for ignoring Undo
    tcatpath = bpy.app.tempdir + "tempcats.json"
    if not os.path.exists(tcatpath):
        with open(tcatpath, 'x', encoding='utf8') as tempfile:
            print(tcatpath)
    return tcatpath

def TempSaveCats(): # save to the create Tempfile
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    tcatpath = CreateTempCats()
    with open(tcatpath, 'r+', encoding='utf8') as tempfile:
        tempfile.truncate(0)
        tempfile.seek(0)
        cats = []
        for cat in AR_Var.Categories:
            cats.append({
                "name": cat.name,
                "pn_name": cat.pn_name,
                "pn_show": cat.pn_show,
                "Instance_Start": cat.Instance_Start,
                "Instance_length": cat.Instance_length
            })
        insts = []
        for inst in AR_Var.Instance_Coll:
            insts.append({
                "name": inst.name,
                "icon": inst.icon,
                "command": [cmd.name for cmd in inst.command]
            })
        data = {
            "Instance_Index": AR_Var.Instance_Index,
            "Categories": cats,
            "Instance_Coll": insts
        }
        json.dump(data, tempfile)

@persistent
def TempLoadCats(dummy): #Load the Created tempfile
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    tcatpath = bpy.app.tempdir + "tempcats.json"
    AR_Var.ar_enum.clear()
    reg = bpy.ops.screen.redo_last.poll()
    if reg:
        for cat in AR_Var.Categories:
            RegisterUnregister_Category(GetPanelIndex(cat), False)
    AR_Var.Categories.clear()
    AR_Var.Instance_Coll.clear()
    with open(tcatpath, 'r', encoding='utf8') as tempfile:
        data = json.load(tempfile)
        inst_coll = data["Instance_Coll"]
        for i in range(len(inst_coll)):
            inst = AR_Var.Instance_Coll.add()
            inst.name = inst_coll[i]["name"]
            inst.icon = inst_coll[i]["icon"]
            for y in range(len(inst_coll[i]["command"])):
                cmd = inst.command.add()
                cmd.name = inst_coll[i]["command"][y]
        index = data["Instance_Index"]
        AR_Var.Instance_Index = index
        for i in range(len(AR_Var.Instance_Coll)):
            new_e = AR_Var.ar_enum.add()
            new_e.name = str(i)
            new_e.Index = i
        AR_Var.ar_enum[index].Value = True
        for cat in data["Categories"]:
            new = AR_Var.Categories.add()
            new.name = cat["name"]
            new.pn_name = cat["pn_name"]
            new.pn_show = cat["pn_show"]
            new.Instance_Start = cat["Instance_Start"]
            new.Instance_length = cat["Instance_length"]
            if reg:
                RegisterUnregister_Category(GetPanelIndex(new))

def CheckForDublicates(l, name, num = 1): #Check for name dublicates and appen .001, .002 etc.
    if name in l:
        return CheckForDublicates(l, name.split(".")[0] +".{0:03d}".format(num), num + 1)
    return name

def AlertTimerPlay(recindex): #Remove alert after time passed for Recored
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Record_Coll[CheckCommand(0)].Command[recindex].alert = False
    for ele in AR_Var.Record_Coll[CheckCommand(recindex + 1)].Command:
        ele.alert = False
    redrawLocalANDMacroPanels()

def AlertTimerCmd(): #Remove alert after time passed for Buttons
    Data.alert_index = None

def Inst_Coll_Insert(index, data, collection): # Insert in "Inst_Coll" Collection
    collection.add()
    for x in range(len(collection) - 1, index, -1):# go the array backwards
        collection[x].name = collection[x - 1].name
        collection[x].icon = collection[x - 1].icon
        collection[x].command.clear()
        for command in collection[x - 1].command:
            cmd = collection[x].command.add()
            cmd.name = command.name
    collection[index].name = data["name"]
    collection[index].icon = CheckIcon(data["icon"])
    collection[index].command.clear()
    for command in data["command"]:
        cmd = collection[index].command.add()
        cmd.name = command

def ImportSortedZip(filepath):
    with zipfile.ZipFile(filepath, 'r') as zip_out:
        filepaths = sorted(zip_out.namelist())
        dirlist = []
        tempdirfiles = []
        dirfileslist = []
        for btn_file in filepaths:
            btn_dirc = btn_file.split("/")[0]
            if btn_dirc not in dirlist:
                if len(tempdirfiles):
                    dirfileslist.append(tempdirfiles[:])
                dirlist.append(btn_dirc)
                tempdirfiles.clear()
            tempdirfiles.append(btn_file)
        else:
            if len(tempdirfiles):
                dirfileslist.append(tempdirfiles)

        sorteddirlist = [None] * len(dirlist)
        for i in range(len(dirlist)):
            if "~" in dirlist[i]:
                new_i = int(dirlist[i].split("~")[0])
                sorteddirlist[new_i] = dirlist[i]
                dirfileslist[new_i], dirfileslist[i] = dirfileslist[i], dirfileslist[new_i]
                sortedfilelist = [None] * len(dirfileslist[new_i])
                for fil in dirfileslist[new_i]:
                    if fil.count("~") == 3 and fil.endswith('.py'):
                        sortedfilelist[int(os.path.basename(fil).split("~")[0])] = fil
                    else:
                        return (None, None)
                dirfileslist[new_i] = sortedfilelist
            else:
                return (None, None)
        return (dirfileslist, sorteddirlist)

def CheckForUpdate():
    try:
        updateSource = request.urlopen(config["checkSource_URL"])
        data = json.loads(updateSource.read().decode("utf-8"))
        updateContent = base64.b64decode(data["content"]).decode("utf-8")
        with open(os.path.join(os.path.dirname(__file__),"__init__.py"), 'r', encoding= "utf-8", errors='ignore') as currentFile:
            currentContext = currentFile.read()
            lines = currentContext.splitlines()
            for i in range(15):
                if lines[i].strip().startswith('"version"'):
                    currentVersion = GetVersion(lines[i])
                    lines = updateContent.splitlines()
                    for j in range(15):
                        if lines[j].strip().startswith('"version"'):
                            updateVersion = GetVersion(lines[j])
                            if updateVersion[0] > currentVersion[0] or (updateVersion[0] == currentVersion[0] and updateVersion[1] > currentVersion[1]) or (updateVersion[0] == currentVersion[0] and updateVersion[1] == currentVersion[1] and updateVersion[2] > currentVersion[2]):
                                return (True, updateVersion)
                            else:
                                return (False, currentVersion)
    except:
        return (False, "no Connection")

def GetVersion(line):
    return eval("(%s)" %line.split("(")[1].split(")")[0])

def CheckForCategotyFile():
    dirpath = os.path.dirname(__file__)
    return os.path.exists(os.path.join(dirpath, "Category.py"))

def Update():
    source = request.urlopen(config["repoSource_URL"] + "/archive/master.zip")
    ExistCat = CheckForCategotyFile()
    with zipfile.ZipFile(BytesIO(source.read())) as extract:
        for exct in extract.namelist():
            tail, head = os.path.split(exct)
            dirpath = os.path.join(bpy.app.tempdir, "AR_Update")
            if not os.path.exists(dirpath):
                os.mkdir(dirpath)
            temppath = os.path.join(dirpath, __package__)
            if not os.path.exists(temppath):
                os.mkdir(temppath)
            if len(tail.split('/')) == 1 and head.endswith(".py"):
                if head == "Category.py" and ExistCat:
                    continue
                with open(os.path.join(temppath, head), 'w', encoding= 'utf8') as tempfile:
                    tempfile.write(extract.read(exct).decode("utf-8"))
        zippath = os.path.join(bpy.app.tempdir, "AR_Update/" + __package__ +".zip")
        with zipfile.ZipFile(zippath, 'w') as zip_it:
            for tempfile in os.listdir(temppath):
                if tempfile.endswith(".py"):
                    currentpath = os.path.join(temppath, tempfile)
                    zip_it.write(currentpath, os.path.join(__package__, tempfile))
                    os.remove(currentpath)
            else:
                os.rmdir(temppath)
        bpy.ops.preferences.addon_install(filepath= zippath)
        os.remove(zippath)
        os.rmdir(dirpath)

def GetCatRadioIndex(selections):
    for sel in selections:
        if sel.selected:
            return sel.index
    return 0

def CreateNewProp(prop):
    name = "Edit_Command_%s" % prop.identifier
    exec("bpy.types.Scene.%s = prop" % name)
    return "bpy.context.scene.%s" % name

def DeleteProps(address):
    exec("del %s" % address)

def getIcons():
    return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()[1:]

def getIconsvalues():
    return [icon.value for icon in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.values()[1:]]

def registerIcon(pcoll, name: str, filepath: str):
    try:
        pcoll.load(name, filepath, 'IMAGE', force_reload= True)
    except:
        split = name.split('.')
        if len(split) > 1 and split[-1].isnumeric():
            name = ".".join(split[:-1]) + str(int(split[-1]) + 1)
        else:
            name = name + ".1"
        registerIcon(pcoll, name, filepath)

def unregisterIcon(pcoll, name: str):
    del pcoll[name]

def LoadIcons(filepath):
    img = bpy.data.images.load(filepath)
    if img.size[0] == img.size[1]:
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        img.scale(32, 32)
        split = img.name.split('.') # last element is format of file
        img.name = '.'.join(split[:-1])
        internalpath = os.path.join(AR_Var.IconFilePath, img.name + "." + split[-1])
        img.save_render(internalpath)
        registerIcon(preview_collections['ar_custom'], "AR_" + img.name, internalpath)
        bpy.data.images.remove(img)
    else:
        bpy.data.images.remove(img)
        return 'The Image must be a square'

def TimerCommads(Commands, index):
    execution_queue.put(functools.partial(Play, Commands, index))

def getAllLoops(Commands):
    datal = []
    for i, Command in enumerate(Commands):
        if Command.active:
            split = Command.cname.split(":")
            if split[0] == 'ar.event':
                data = json.loads(":".join(split[1:]))
                if data['Type'] == 'Loop':
                    datal.append({'Loop': i})
                elif data['Type'] == 'EndLoop':
                    index = CheckForLoopEnd(datal)
                    if index != -1:
                        datal[index]['End'] = i
    return [obj for obj in datal if 'End' in obj]

def CheckForLoopEnd(data):
    if len(data) < 1:
        return -1
    if 'End' in data[-1]:
        return CheckForLoopEnd(data[:-1])
    else:
        return len(data) - 1 

def getIndexInLoop(i, AllLoops, identifier):
    for li in range(len(AllLoops)):
        if identifier in AllLoops[li] and i == AllLoops[li][identifier]:
            return li

def runRenderComplete(dummy):
    for index, Commands in Data.Commands_RenderComplete:
        Play(Commands, index)
    Data.Commands_RenderComplete.clear()

def runRenderInit(dummy):
    for index, Commands in Data.Commands_RenderInit:
        Play(Commands, index)
    Data.Commands_RenderInit.clear()

@persistent
def SaveToDataHandler(dummy):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    local = []
    for ele in AR_Var.Record_Coll:
        loc = {}
        loc['name'] = ele.name
        loc['Index'] = ele.Index
        loc['Command'] = []
        for cmd in ele.Command:
            locmd = {}
            locmd['cname'] = cmd.cname
            locmd['macro'] = cmd.macro
            locmd['active'] = cmd.active
            locmd['alert'] = cmd.alert
            locmd['icon'] = cmd.icon
            loc['Command'].append(locmd)
        local.append(loc)
    bpy.context.scene.ar_local = json.dumps(local)

def WriteCatVis(data):
    with open(catVisPath, 'w', encoding= 'utf8') as catfile:
        catfile.write("Category = " + json.dumps(data, indent=4))

def getCatInAreas(cat, data):
    l = []
    for i in data['Area'].items():
        if cat == i[1]:
            l.append(i[0])
    return l

def Alert(index):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Record_Coll[CheckCommand(0)].Command[index].alert = True
    bpy.app.timers.register(functools.partial(AlertTimerPlay, index), first_interval = 1)
    try:
        bpy.context.area.tag_redraw()
    except:
        redrawLocalANDMacroPanels()

def redrawLocalANDMacroPanels():
    for i in classespanel:
        if i.__name__.startswith("AR_PT_Local_") or i.__name__.startswith("AR_PT_MacroEditer_"):
            bpy.utils.unregister_class(i)
            bpy.utils.register_class(i)

def CheckIcon(icon):
    if isinstance(icon, int):
        return icon
    if icon.isnumeric():
        icon = int(icon)
    else:
        iconlist = getIcons()
        if icon in iconlist:
            icon = getIconsvalues()[iconlist.index(icon)]
        else:
            icon = 101 # Icon: BLANK1
    return icon

def LoadActionFromTexteditor(texts):
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    AR_Var.Record_Coll.clear()
    for text in texts:
        if bpy.data.texts.find(text) == -1:
            continue
        text = bpy.data.texts[text]
        lines = [line.body for line in text.lines]
        Add(0, text.name)
        for line in lines:
            print(line)
            if line != '':
                AR_Var = bpy.context.preferences.addons[__package__].preferences
                Add(len(AR_Var.Record_Coll[0].Command), line)

def showCategory(name, context):
    AR_Var = context.preferences.addons[__package__].preferences
    if AR_Var.ShowAllCategories:
        return True
    if name in CatVisibility["Area"][context.area.ui_type]:
        return True
    if context.area.ui_type == "VIEW_3D":
        if name in CatVisibility["Mode"][context.mode]:    
            return True
    l = []
    for ele in CatVisibility["Area"].values():
        for item in ele:
            l.append(item)
    for ele in CatVisibility["Mode"].values():
        for item in ele:
            l.append(item)
    return not (name in l)
# endregion

# region Panels
def panelFactory(spaceType): #Create Panels for every spacetype with UI

    class AR_PT_Local(Panel):
        bl_space_type = spaceType
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Local Actions'
        bl_idname = "AR_PT_Local_%s" % spaceType
        bl_order = 0

        '''def draw_header(self, context):
            self.layout.label(text = '', icon = 'REC')'''

        def draw(self, context):
            AR_Var = context.preferences.addons[__package__].preferences
            scene = bpy.context.scene
            layout = self.layout
            if AR_Var.AutoUpdate and AR_Var.Update:
                box = layout.box()
                box.label(text= "A new Version is available (" + AR_Var.Version + ")")
                box.operator(AR_OT_Update.bl_idname, text= "Update")
            box = layout.box()
            box_row = box.row()
            col = box_row.column()
            col.template_list('AR_UL_Selector' , '' , AR_Var.Record_Coll[CheckCommand(0)] , 'Command' , AR_Var.Record_Coll[CheckCommand(0)] , 'Index', rows=4, sort_lock= True)
            col = box_row.column()
            col2 = col.column(align= True)
            col2.operator(AR_OT_Record_Add.bl_idname , text='' , icon='ADD' )
            col2.operator(AR_OT_Record_Remove.bl_idname , text='' , icon='REMOVE' )
            col2 = col.column(align= True)
            col2.operator(AR_OT_Record_MoveUp.bl_idname , text='' , icon='TRIA_UP' )
            col2.operator(AR_OT_Record_MoveDown.bl_idname , text='' , icon='TRIA_DOWN' )
    AR_PT_Local.__name__ = "AR_PT_Local_%s" % spaceType
    classespanel.append(AR_PT_Local)

    class AR_PT_MacroEditer(Panel):
        bl_space_type = spaceType
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Macro Editor'
        bl_idname = "AR_PT_MacroEditer_%s" % spaceType
        bl_order = 1

        def draw(self, context):
            AR_Var = context.preferences.addons[__package__].preferences
            scene = context.scene
            layout = self.layout
            box = layout.box()
            box_row = box.row()
            col = box_row.column()
            col.template_list('AR_UL_Command' , '' , AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)] , 'Command' , AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)] , 'Index', rows=4)
            col = box_row.column()
            if not AR_Prop.Record :
                col2 = col.column(align= True)
                col2.operator(AR_OT_Command_Add.bl_idname , text='' , icon='ADD' )
                col2.operator(AR_OT_AddEvent.bl_idname, text= '', icon= 'MODIFIER').Num = -1
                col2.operator(AR_OT_Command_Remove.bl_idname , text='' , icon='REMOVE' )
                col2 = col.column(align= True)
                col2.operator(AR_OT_Command_MoveUp.bl_idname , text='' , icon='TRIA_UP' )
                col2.operator(AR_OT_Command_MoveDown.bl_idname , text='' , icon='TRIA_DOWN' )
            #----------------------------------------
            row = layout.row()
            if AR_Prop.Record :
                row.scale_y = 2
                row.operator(AR_OT_Record_Stop.bl_idname , text='Stop')
            else :
                row2 = row.row(align= True)
                row2.operator(AR_OT_Record_Start.bl_idname , text='Record' , icon='REC' )
                row2.operator(AR_OT_Command_Clear.bl_idname , text= 'Clear')
                col = layout.column()
                row = col.row()
                row.scale_y = 2
                row.operator(AR_OT_Record_Play.bl_idname , text='Play' )
                col.operator(AR_OT_RecordToButton.bl_idname , text='Local to Global' )
                row = col.row(align= True)
                row.enabled = len(AR_Var.Record_Coll[CheckCommand(0)].Command) > 0
                row.prop(AR_Var, 'RecToBtn_Mode', expand= True)
    AR_PT_MacroEditer.__name__ = "AR_PT_MacroEditer_%s" % spaceType
    classespanel.append(AR_PT_MacroEditer)

    class AR_PT_Global(Panel):
        bl_space_type = spaceType
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Global Actions'
        bl_idname = "AR_PT_Global_%s" % spaceType
        bl_order = 2

        def draw_header(self, context):
            AR_Var = context.preferences.addons[__package__].preferences
            layout = self.layout
            row = layout.row(align= True)
            row.prop(AR_Var, 'HideMenu', icon= 'COLLAPSEMENU', text= "", emboss= True)

        def draw(self, context):
            AR_Var = context.preferences.addons[__package__].preferences
            scene = bpy.context.scene
            layout = self.layout
            if not AR_Var.HideMenu:
                col = layout.column()
                row = col.row()
                row.scale_y = 2
                row.operator(AR_OT_ButtonToRecord.bl_idname, text='Global to Local' )
                row = col.row(align= True)
                row.enabled =  len(AR_Var.Instance_Coll) > 0
                row.prop(AR_Var, 'BtnToRec_Mode', expand= True)
                row = layout.row().split(factor= 0.4)
                row.label(text= 'Buttons')
                row2 = row.row(align= True)
                row2.operator(AR_OT_Button_MoveUp.bl_idname , text='' , icon='TRIA_UP' )
                row2.operator(AR_OT_Button_MoveDown.bl_idname , text='' , icon='TRIA_DOWN' )
                row2.operator(AR_OT_Category_MoveButton.bl_idname, text= '', icon= 'PRESET')
                row2.operator(AR_OT_Button_Remove.bl_idname, text='' , icon='TRASH' )
                row = layout.row()
                row2 = row.split(factor= 0.7)
                col = row2.column()
                col.enabled = len(AR_Var.Instance_Coll) > 0 and not (multiselection_buttons[0] and len(InstanceLastselected) > 1)
                col.prop(AR_Var , 'Rename' , text='')
                row2.operator(AR_OT_Button_Rename.bl_idname , text='ReName')
    AR_PT_Global.__name__ = "AR_PT_Global_%s" % spaceType
    classespanel.append(AR_PT_Global)

    class AR_PT_Help(Panel):
        bl_space_type = spaceType
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Help'
        bl_idname = "AR_PT_Help_%s" % spaceType
        bl_options = {'DEFAULT_CLOSED'}
        bl_order = 3

        def draw_header(self, context):
            layout = self.layout
            layout.label(icon= 'INFO')

        def draw(self, context):
            layout = self.layout
            AR_Var = context.preferences.addons[__package__].preferences
            layout.operator(AR_OT_Help_OpenURL.bl_idname, text= "Manual", icon= 'ASSET_MANAGER').url = config["Manual_URL"]
            layout.operator(AR_OT_Help_OpenURL.bl_idname, text= "Hint", icon= 'HELP').url = config["Hint_URL"]
            layout.operator(AR_OT_Help_OpenURL.bl_idname, text= "Bug Report", icon= 'URL').url = config["BugReport_URL"]
            row = layout.row()
            if AR_Var.Update:
                row.operator(AR_OT_Update.bl_idname, text= "Update")
                row.operator(AR_OT_ReleaseNotes.bl_idname, text= "Release Notes")
            else:
                row.operator(AR_OT_CheckUpdate.bl_idname, text= "Check For Updates")
                if AR_Var.Restart:
                    row.operator(AR_OT_Restart.bl_idname, text= "Restart to Finsih")
            if AR_Var.Version != '':
                if AR_Var.Update:
                    layout.label(text= "new Version available (" + AR_Var.Version + ")")
                else:
                    layout.label(text= "latest Vesion installed (" + AR_Var.Version + ")")
    AR_PT_Help.__name__ = "AR_PT_Help_%s" % spaceType
    classespanel.append(AR_PT_Help)

    class AR_PT_Advanced(Panel):
        bl_space_type = spaceType
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Advanced'
        bl_idname = "AR_PT_Advanced_%s" % spaceType
        #bl_parent_id = AR_PT_Global.bl_idname
        bl_options = {'DEFAULT_CLOSED'}
        bl_order = 4

        def draw(self, context):
            AR_Var = context.preferences.addons[__package__].preferences
            layout = self.layout
            col = layout.column()
            col.label(text= "Category", icon= 'GROUP')
            row = col.row(align= True)
            selectedCat_index = GetCatRadioIndex(AR_Var.Selected_Category)
            row.label(text= '')
            row2 = row.row(align= True)
            row2.scale_x = 1.5
            row2.operator(AR_OT_Category_MoveUp.bl_idname, text= '',icon= 'TRIA_UP').Index = selectedCat_index
            row2.operator(AR_OT_Category_MoveDown.bl_idname, text= '',icon= 'TRIA_DOWN').Index = selectedCat_index
            row2.operator(AR_OT_Category_Add.bl_idname, text= '', icon= 'ADD').edit = False
            row2.operator(AR_OT_Category_Delete.bl_idname, text= '', icon= 'TRASH')
            row.label(text= '')
            row = col.row(align= False)
            row.operator(AR_OT_Category_Edit.bl_idname, text= 'Edit')
            row.prop(AR_Var, 'ShowAllCategories', text= "", icon= 'RESTRICT_VIEW_OFF' if AR_Var.ShowAllCategories else 'RESTRICT_VIEW_ON')
            col.label(text= "Data Management", icon= 'FILE_FOLDER')
            col.operator(AR_OT_Import.bl_idname, text= 'Import')
            col.operator(AR_OT_Export.bl_idname, text= 'Export')
            col.label(text= "Storage File Settings", icon= "FOLDER_REDIRECT")
            row = col.row()
            row.label(text= "AutoSave")
            row.prop(AR_Var, 'Autosave', toggle= True, text= "On" if AR_Var.Autosave else "Off")
            col.operator(AR_OT_Save.bl_idname , text='Save to File' )
            col.operator(AR_OT_Load.bl_idname , text='Load from File' )
            col.operator(AR_OT_Record_LoadLoaclActions.bl_idname, text='Load Local Actions')
            col.label(text= "Local Settings")
            col.prop(AR_Var, 'CreateEmpty', text= "Create Empty Macro on Error")
    AR_PT_Advanced.__name__ = "AR_PT_Advanced_%s" % spaceType
    classespanel.append(AR_PT_Advanced)

def RegisterCategories(): #Register all Categories
    for i in range(catlength[0]):
        RegisterUnregister_Category(i)

def RegisterUnregister_Category(index, register = True): #Register/Unregister one Category
    for spaceType in spaceTypes:
        class AR_PT_Category(Panel):
            bl_space_type = spaceType
            bl_region_type = 'UI'
            bl_category = 'Action Recorder'
            bl_label = ' '
            bl_idname = "AR_PT_Category_%s_%s" %(index, spaceType)
            bl_parent_id = "AR_PT_Global_%s" % spaceType
            bl_order = index + 1

            @classmethod
            def poll(self, context):
                AR_Var = context.preferences.addons[__package__].preferences
                index = int(self.bl_idname.split("_")[3])
                category = AR_Var.Categories[index]
                return showCategory(category.pn_name, context)

            def draw_header(self, context):
                AR_Var = context.preferences.addons[__package__].preferences
                index = int(self.bl_idname.split("_")[3])
                category = AR_Var.Categories[index]
                layout = self.layout
                row = layout.row()
                row.prop(AR_Var.Selected_Category[index], 'selected', text= '', icon= 'LAYER_ACTIVE' if AR_Var.Selected_Category[index].selected else 'LAYER_USED', emboss= False)
                row.label(text= category.pn_name)

            def draw(self, context):
                AR_Var = context.preferences.addons[__package__].preferences
                scene = context.scene
                index = int(self.bl_idname.split("_")[3])
                category = AR_Var.Categories[index]
                layout = self.layout
                col = layout.column()
                for i in range(category.Instance_Start, category.Instance_Start + category.Instance_length):
                    row = col.row(align=True)
                    row.alert = Data.alert_index == i
                    row.prop(AR_Var.ar_enum[i], 'Value' ,toggle = 1, icon= 'LAYER_ACTIVE' if AR_Var.ar_enum[i].Value else 'LAYER_USED', text= "", event= True)
                    row.operator(AR_OT_Category_Cmd_Icon.bl_idname, text= "", icon_value= AR_Var.Instance_Coll[i].icon).index = i
                    row.operator(AR_OT_Category_Cmd.bl_idname , text= AR_Var.Instance_Coll[i].name).Index = i
        AR_PT_Category.__name__ = "AR_PT_Category_%s_%s" %(index, spaceType)
        if register:
            bpy.utils.register_class(AR_PT_Category)
            categoriesclasses.append(AR_PT_Category)
        else:
            try:
                panel = eval("bpy.types." + AR_PT_Category.__name__)
                bpy.utils.unregister_class(panel)
                categoriesclasses.remove(panel)
            except:
                pass
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if register:
        new = AR_Var.Selected_Category.add()
        new.index = index
    else:
        AR_Var.Selected_Category.remove(len(AR_Var.Selected_Category) - 1)
    if GetCatRadioIndex(AR_Var.Selected_Category) is None and len(AR_Var.Selected_Category):
        AR_Var.Selected_Category[0].selected = True
# endregion
        
# region Opertators
class AR_OT_Category_Add(Operator):
    bl_idname = "ar.category_add"
    bl_label = "Add Category"

    Name : StringProperty(name = "Name", default="")
    ModeItems = [("NONE", "None", "", "SELECT_SET", 0),
                ("EDIT_MESH", "Edit Mode Meshe", "", "EDITMODE_HLT", 1),
                ("EDIT_CURVE", "Edit Mode Curve", "", "EDITMODE_HLT", 2),
                ("EDIT_SURFACE", "Edit Mode Surface", "", "EDITMODE_HLT", 3),
                ("EDIT_TEXT", "Edit Mode Text", "", "EDITMODE_HLT", 4),
                ("EDIT_ARMATURE", "Edit Mode Armature", "", "EDITMODE_HLT", 5),
                ("EDIT_METABALL", "Edit Mode Metaball", "", "EDITMODE_HLT", 6),
                ("EDIT_LATTICE", "Edit Mode Lattice", "", "EDITMODE_HLT", 7),
                ("POSE", "Pose", "", "POSE_HLT", 8),
                ("SCULPT", "Sculpt Mode", "", "SCULPTMODE_HLT", 9),
                ("PAINT_WEIGHT", "Weight Paint", "", "WPAINT_HLT", 10),
                ("PAINT_VERTEX", "Vertex Paint", "", "VPAINT_HLT", 11), 
                ("PAINT_TEXTURE", "Texture Paint", "", "TPAINT_HLT", 12),
                ("PARTICLE", "Particle Edit", "", "PARTICLEMODE", 13),
                ("OBJECT", "Object Mode", "", "OBJECT_DATAMODE", 14),
                ("PAINT_GPENCIL", "Draw", "", "GREASEPENCIL", 15),
                ("EDIT_GPENCIL", "Edit Mode Grease Pencil", "", "EDITMODE_HLT", 16),
                ("SCULPT_GPENCIL", "Sculpt Mode Grease Pencil", "", "SCULPTMODE_HLT", 17),
                ("WEIGHT_GPENCIL", "Weight Paint Grease Pencil", "", "WPAINT_HLT", 18),
                ("VERTEX_GPENCIL", "Vertex Paint Grease Pencil", "", "VPAINT_HLT", 19)]
    AreaItems = [("NONE", "None", "", "SELECT_SET", 0),
                ("VIEW_3D", "3D Viewport", "", "VIEW3D", 1),
                ("VIEW", "Image Editor", "", "IMAGE", 2),
                ("UV", "UV Editor", "", "UV", 3),
                ("CompositorNodeTree", "Compositor", "", "NODE_COMPOSITING", 4),
                ("TextureNodeTree", "Texture Node Editor", "", "NODE_TEXTURE", 5),
                ("ShaderNodeTree", "Shader Editor", "", "NODE_MATERIAL", 6),
                ("SEQUENCE_EDITOR", "Video Sequencer", "", "SEQUENCE", 7),
                ("CLIP_EDITOR", "Movie Clip Editor", "", "TRACKER", 8),
                ("DOPESHEET", "Dope Sheet", "", "ACTION", 9),
                ("TIMELINE", "Timeline", "", "TIME", 10),
                ("FCURVES", "Graph Editor", "", "GRAPH", 11),
                ("DRIVERS", "Drivers", "", "DRIVER", 12),
                ("NLA_EDITOR", "Nonlinear Animation", "", "NLA", 13),
                ("TEXT_EDITOR", "Text Editor", "", "TEXT", 14)]
    Area : EnumProperty(items= AreaItems, name= "Area", default= "NONE")
    Mode : EnumProperty(items= ModeItems, name= "Mode", default= "NONE")
    lastName : StringProperty(name= "Internal", default= "")
    edit : BoolProperty(default= False, name= "Internal")
    catName : StringProperty(name= "Internal")
    CancelDataArea = []
    CancelDataMode = []

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        scene = context.scene
        if self.edit:
            new = AR_Var.Categories[self.catName]
            name = self.Name
        else:
            new = AR_Var.Categories.add()
            name = CheckForDublicates([n.pn_name for n in AR_Var.Categories], self.Name)
        new.name = name
        new.pn_name = name
        if not self.edit:
            new.Instance_Start = len(AR_Var.Instance_Coll)
            new.Instance_length = 0
            RegisterUnregister_Category(GetPanelIndex(new))
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        for ele in Data.CatVisis:
            if ele[0] != 'NONE':
                CatVisibility['Area'][self.AreaItems[ele[0]][0]].append(name)
            elif ele[1] != 'NONE':
                CatVisibility['Mode'][self.ModeItems[ele[1]][0]].append(name)
        WriteCatVis(CatVisibility)
        Data.CatVisis.clear()
        return {"FINISHED"}

    def invoke(self, context, event):
        if self.edit:
            self.CancelDataArea.clear()
            self.CancelDataMode.clear()
            name = self.catName
            self.Name = name
            for area in CatVisibility['Area']:
                if name in CatVisibility['Area'][area]:
                    self.CancelDataArea.append(area)
                    CatVisibility['Area'][area].remove(name)
                    bpy.ops.ar.category_applyvisibility('EXEC_DEFAULT', Area= area, Mode= 'NONE')
            for mode in CatVisibility['Mode']:
                if name in CatVisibility['Mode'][mode]:
                    self.CancelDataMode.append(mode)
                    CatVisibility['Mode'][mode].remove(name)
                    bpy.ops.ar.category_applyvisibility('EXEC_DEFAULT', Area= 'VIEW_3D', Mode= mode)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        layout = self.layout
        layout.prop(self, 'Name')
        layout.prop(self, 'Area')
        if self.Area == 'VIEW_3D':
            layout.prop(self, 'Mode')
        ops = layout.operator(AR_OT_Category_Apply_Visibility.bl_idname)
        ops.Area = self.Area
        ops.Mode = self.Mode
        if len(Data.CatVisis) > 0:
            box = layout.box()
            row = box.row()
            row.label(text= "Area")
            row.label(text= "Mode")
            row.label(icon= 'BLANK1')
            for i, vis in enumerate(Data.CatVisis):
                row = box.row()
                if vis[1] == 'NONE':
                    row.label(text= self.AreaItems[vis[0]][1])
                    row.label(text= "")
                    row.operator(AR_OT_Category_Delete_Visibility.bl_idname, text= '', icon= 'PANEL_CLOSE', emboss= False).index = i    
                else:
                    row.label(text= "3D Viewport")
                    row.label(text= self.ModeItems[vis[1]][1])
                    row.operator(AR_OT_Category_Delete_Visibility.bl_idname, text= '', icon= 'PANEL_CLOSE', emboss= False).index = i

    def cancel(self, context):
        name = self.Name
        for area in self.CancelDataArea:
            CatVisibility['Area'][area].append(name)
        for mode in self.CancelDataMode:
            CatVisibility['Mode'][mode].append(name)
        Data.CatVisis.clear()
classes.append(AR_OT_Category_Add)

class AR_OT_Category_Apply_Visibility(Operator):
    bl_idname = "ar.category_applyvisibility"
    bl_label = "Apply Visibility"
    bl_description = ""
    bl_options = {"INTERNAL"}

    Mode : StringProperty()
    Area : StringProperty()

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        if self.Area != "NONE":
            if self.Area == 'VIEW_3D' and self.Mode != "NONE":
                if self.Mode not in [ele[1] for ele in Data.CatVisis]:
                    for i in AR_OT_Category_Add.ModeItems:
                        if i[0] == self.Mode:
                            index = i[4]
                    Data.CatVisis.append(('NONE', index))
            else:
                if self.Area not in [ele[0] for ele in Data.CatVisis]:
                    for i in AR_OT_Category_Add.AreaItems:
                        if i[0] == self.Area:
                            index = i[4]
                    Data.CatVisis.append((index, 'NONE'))
        return {"FINISHED"}
classes.append(AR_OT_Category_Apply_Visibility)

class AR_OT_Category_Delete_Visibility(Operator):
    bl_idname = "ar.category_deletevisibility"
    bl_label = "Delete Visibility"
    bl_description = ""

    index : IntProperty()

    def execute(self, context):
        Data.CatVisis.pop(self.index)
        return {"FINISHED"}
classes.append(AR_OT_Category_Delete_Visibility)

class AR_OT_Category_Delete(Operator):
    bl_idname = "ar.category_delete"
    bl_label = "Delete Category"
    bl_description = "Delete the selected Category"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Categories)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        scene = context.scene
        index = GetCatRadioIndex(AR_Var.Selected_Category)
        if not index is None:
            cat = categories[index]
            name = cat.pn_name
            start = cat.Instance_Start
            for i in range(start, start + cat.Instance_length):
                AR_Var.ar_enum.remove(len(AR_Var.ar_enum) - 1)
                AR_Var.Instance_Coll.remove(start)
            for nextcat in categories[index + 1 :]:
                nextcat.Instance_Start -= cat.Instance_length
            categories.remove(index)
            RegisterUnregister_Category(len(categories), False)
            SetEnumIndex()
            for area in CatVisibility['Area']:
                if name in CatVisibility['Area'][area]: 
                    CatVisibility['Area'][area].remove(name)
            for mode in CatVisibility['Mode']:
                if name in CatVisibility['Mode'][mode]:
                    CatVisibility['Mode'][mode].remove(name)
            WriteCatVis(CatVisibility)
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
    
    def draw(self, context):    
        AR_Var = context.preferences.addons[__package__].preferences    
        layout = self.layout
        layout.label(text= "All Actions in this Category will be deleted", icon= 'ERROR')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_Category_Delete)

class AR_OT_Category_Edit(Operator):
    bl_idname = "ar.category_edit"
    bl_label = "Edit Category"
    bl_description = "Edit the selected Category"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Categories)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        index = None
        for cat in AR_Var.Selected_Category:
            if cat.selected:
                index = cat.index
        if index != None:
            bpy.ops.ar.category_add('INVOKE_DEFAULT', edit= True, catName= AR_Var.Categories[index].pn_name) 
        return {"FINISHED"}
classes.append(AR_OT_Category_Edit)

class AR_OT_Category_MoveButton(Operator):
    bl_idname = "ar.category_move_category_button"
    bl_label = "Move Action Button"
    bl_description = "Move the selected Action Button of a Category to Another Category"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        scene = context.scene
        for cat in categories:
            if cat.pn_selected:
                l = []
                if multiselection_buttons[0]:
                    for i in range(len(AR_Var.ar_enum)):
                        if AR_Var.ar_enum[i].Value:
                            l.append(i)
                else:
                    l.append(AR_Var.Instance_Index)
                offset = 0
                for Index in l:
                    Index = Index - offset
                    catendl = cat.Instance_Start + cat.Instance_length
                    for curcat in categories:
                        if Index >= curcat.Instance_Start and Index < curcat.Instance_Start + curcat.Instance_length:
                            curcat.Instance_length -= 1
                            for nextcat in categories[GetPanelIndex(curcat) + 1 :]:
                                nextcat.Instance_Start -= 1
                            break
                    data ={
                        "name": AR_Var.Instance_Coll[Index].name,
                        "icon": AR_Var.Instance_Coll[Index].icon,
                        "command": [cmd.name for cmd in AR_Var.Instance_Coll[Index].command]
                    }
                    AR_Var.Instance_Coll.remove(Index)
                    Inst_Coll_Insert(catendl - 1 * (Index < catendl), data, AR_Var.Instance_Coll)
                    offset += 1 * (Index < catendl)
                    for nextcat in categories[GetPanelIndex(cat) + 1:]:
                        nextcat.Instance_Start += 1
                    cat.Instance_length += 1
                SetEnumIndex()
                break
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}

    def draw(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        layout = self.layout
        for cat in categories:
            layout.prop(cat, 'pn_selected', text= cat.pn_name)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_Category_MoveButton)

class AR_OT_Category_MoveUp(Operator):
    bl_idname = "ar.category_move_up"
    bl_label = "Move Up"
    bl_description = "Move the Category up"

    Index : IntProperty()

    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        i = self.Index
        categories = AR_Var.Categories
        y = i - 1
        if y >= 0:
            cat2 = categories[y]
            while not showCategory(cat2.pn_name, context):
                y -= 1
                if y < 0:
                    return {"CANCELLED"}
                cat2 = categories[y]
            cat1 = categories[i]
            cat1.name, cat2.name = cat2.name, cat1.name
            cat1.pn_name, cat2.pn_name = cat2.pn_name, cat1.pn_name
            cat1.pn_show, cat2.pn_show = cat2.pn_show, cat1.pn_show
            cat1.pn_selected, cat2.pn_selected = cat2.pn_selected, cat1.pn_selected
            cat1.Instance_Start, cat2.Instance_Start = cat2.Instance_Start, cat1.Instance_Start
            cat1.Instance_length, cat2.Instance_length = cat2.Instance_length, cat1.Instance_length
            AR_Var.Selected_Category[y].selected = True
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Category_MoveUp)

class AR_OT_Category_MoveDown(Operator):
    bl_idname = "ar.category_move_down"
    bl_label = "Move Down"
    bl_description = "Move the Category down"

    Index : IntProperty()

    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        i = self.Index
        categories = AR_Var.Categories
        y = i + 1 
        if y < len(categories):
            cat2 = categories[y]
            while not showCategory(cat2.pn_name, context):
                y += 1
                if y >= len(categories):
                    return {"CANCELLED"}
                cat2 = categories[y]
            cat1 = categories[i]
            cat1.name, cat2.name = cat2.name, cat1.name
            cat1.pn_name, cat2.pn_name = cat2.pn_name, cat1.pn_name
            cat1.pn_show, cat2.pn_show = cat2.pn_show, cat1.pn_show
            cat1.pn_selected, cat2.pn_selected = cat2.pn_selected, cat1.pn_selected
            cat1.Instance_Start, cat2.Instance_Start = cat2.Instance_Start, cat1.Instance_Start
            cat1.Instance_length, cat2.Instance_length = cat2.Instance_length, cat1.Instance_length
            AR_Var.Selected_Category[y].selected = True
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Category_MoveDown)

class AR_OT_RecordToButton(Operator):
    bl_idname = "ar.record_record_to_button"
    bl_label = "Action to Global"
    bl_description = "Add the selected Action to a Category"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        if len(categories):
            for cat in categories:
                if cat.pn_selected:
                    Recorder_to_Instance(cat)
                    break
            if AR_Var.RecToBtn_Mode == 'move':
                Remove(0)
                TempUpdate()
            TempSaveCats()
            if AR_Var.Autosave:
                Save()
            bpy.context.area.tag_redraw()
            return {"FINISHED"}
        else:
            return {'CANCELLED'}

    def draw(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        layout = self.layout
        if len(categories):
            for cat in categories:
                layout.prop(cat, 'pn_selected', text= cat.pn_name)
        else:
            box = layout.box()
            col = box.column()
            col.scale_y = 0.9
            col.label(text= 'Please Add a Category first', icon= 'INFO')
            col.label(text= 'To do that, go to the Advanced menu', icon= 'BLANK1')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_RecordToButton)

class AR_OT_Import(Operator, ImportHelper):
    bl_idname = "ar.data_import"
    bl_label = "Import"
    bl_description = "Import the Action file into the storage"

    filter_glob: StringProperty( default='*.zip', options={'HIDDEN'} )

    Category : StringProperty(default= "Imports")
    AddNewCategory : BoolProperty(default= False)
    Mode : EnumProperty(name= 'Mode', items= [("add","Add",""),("overwrite", "Overwrite", "")])

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        scene = context.scene
        ar_categories = AR_Var.Categories
        if self.filepath.endswith(".zip"):
            if self.AddNewCategory:
                dirfileslist, sorteddirlist = ImportSortedZip(self.filepath)
                with zipfile.ZipFile(self.filepath, 'r') as zip_out:
                    mycat = ar_categories.add()
                    name = CheckForDublicates([n.pn_name for n in ar_categories], self.Category)
                    mycat.name = name
                    mycat.pn_name = name
                    mycat.Instance_Start = len(AR_Var.Instance_Coll)
                    RegisterUnregister_Category(GetPanelIndex(mycat))
                    for dirs in dirfileslist:
                        for btn_file in dirs:
                            name_icon = os.path.splitext(os.path.basename(btn_file))[0]
                            name = "".join(name_icon.split("~")[1:-1])
                            inst = AR_Var.Instance_Coll.add()
                            inst.name = CheckForDublicates([AR_Var.Instance_Coll[i].name for i in range(mycat.Instance_Start, mycat.Instance_Start + mycat.Instance_length)], name)
                            inst.icon = CheckIcon(name_icon.split("~")[-1])
                            for line in zip_out.read(btn_file).decode("utf-8").splitlines():
                                cmd = inst.command.add()
                                cmd.name = line
                            new_e = AR_Var.ar_enum.add()
                            e_index = len(AR_Var.ar_enum) - 1
                            new_e.name = str(e_index)
                            new_e.Index = e_index
                            mycat.Instance_length += 1
            else:
                if not len(AR_Var.Importsettings):
                    if bpy.ops.ar.data_import_options('EXEC_DEFAULT', filepath= self.filepath, fromoperator= True) == {'CANCELLED'}:
                        self.report({'ERROR'}, "The selected file is not compatible")
                        return {'CANCELLED'}
                for icat in AR_Var.Importsettings:
                    Index = -1
                    mycat = None
                    if icat.enum == 'append':
                        Index = AR_Var.Categories.find(icat.cat_name)
                    if Index == -1:
                        mycat = ar_categories.add()
                        name = icat.cat_name
                        name = CheckForDublicates([n.pn_name for n in ar_categories], name)
                        mycat.name = name
                        mycat.pn_name = name
                        mycat.Instance_Start = len(AR_Var.Instance_Coll)
                        RegisterUnregister_Category(GetPanelIndex(mycat))
                    else:
                        mycat = ar_categories[Index]
                        for btn in icat.Buttons:
                            if btn.enum == 'overwrite':
                                for i in range(mycat.Instance_Start, mycat.Instance_Start + mycat.Instance_length):
                                    inst = AR_Var.Instance_Coll[i]
                                    if btn.btn_name == inst.name:
                                        inst.name = btn.btn_name
                                        inst.icon = CheckIcon(btn.icon)
                                        inst.command.clear()
                                        for cmd in btn.command.splitlines():
                                            new = inst.command.add()
                                            new.name = cmd
                                        break
                                else:
                                    btn.enum = 'add'

                    for btn in icat.Buttons:
                        if btn.enum == 'overwrite':
                            continue
                        inserti = mycat.Instance_Start + mycat.Instance_length
                        name = btn.btn_name
                        icon = btn.icon
                        data = {"name": CheckForDublicates([AR_Var.Instance_Coll[i].name for i in range(mycat.Instance_Start, mycat.Instance_Start + mycat.Instance_length)], name),
                                "command": btn.command.splitlines(),
                                "icon": icon}
                        Inst_Coll_Insert(inserti, data, AR_Var.Instance_Coll)
                        new_e = AR_Var.ar_enum.add()
                        e_index = len(AR_Var.ar_enum) - 1
                        new_e.name = str(e_index)
                        new_e.Index = e_index
                        mycat.Instance_length += 1
                        if Index != -1:
                            for cat in ar_categories[Index + 1:] :
                                cat.Instance_Start += 1
            SetEnumIndex()
            if AR_Var.Autosave:
                Save()
        else:
            self.report({'ERROR'}, "{ " + self.filepath + " } Select a .zip file")
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Importsettings.clear()
        TempSaveCats()
        return {"FINISHED"}
    
    def draw(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        layout = self.layout
        layout.prop(self, 'AddNewCategory', text= "Append to new Category")
        if self.AddNewCategory:
            layout.prop(self, 'Category', text= "Name")
        else:
            layout.operator(AR_OT_ImportLoadSettings.bl_idname, text= "Load Importsettings").filepath = self.filepath
            for cat in AR_Var.Importsettings:
                box = layout.box()
                col = box.column()
                row = col.row()
                if cat.show:
                    row.prop(cat, 'show', icon="TRIA_DOWN", text= "", emboss= False)
                else:
                    row.prop(cat, 'show', icon="TRIA_RIGHT", text= "", emboss= False)
                row.label(text= cat.cat_name)
                row.prop(cat, 'enum', text= "")
                if cat.show:
                    col = box.column()
                    for btn in cat.Buttons:
                        row = col.row()
                        row.label(text= btn.btn_name)
                        if cat.enum == 'append':
                            row.prop(btn, 'enum', text= "")
        
    def cancel(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Importsettings.clear()
classes.append(AR_OT_Import)

class AR_OT_ImportLoadSettings(Operator):
    bl_idname = "ar.data_import_options"
    bl_label = "Load Importsettings"
    bl_description = "Load the select the file to change the importsettings"

    filepath : StringProperty()
    fromoperator : BoolProperty()

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        if os.path.exists(self.filepath) and self.filepath.endswith(".zip"):
            dirfileslist, sorteddirlist = ImportSortedZip(self.filepath)
            if dirfileslist is None:
                if not self.fromoperator:
                    self.report({'ERROR'}, "The selected file is not compatible")
                self.fromoperator = False
                return {'CANCELLED'}
            with zipfile.ZipFile(self.filepath, 'r') as zip_out:
                AR_Var.Importsettings.clear()
                for i in range(len(sorteddirlist)):
                    cat = AR_Var.Importsettings.add()
                    cat.cat_name = "".join(sorteddirlist[i].split("~")[1:])
                    for dir_file in dirfileslist[i]:
                        btn = cat.Buttons.add()
                        name_icon = os.path.splitext(os.path.basename(dir_file))[0]
                        btn.btn_name = "".join(name_icon.split("~")[1:-1])
                        btn.icon = name_icon.split("~")[-1]
                        btn.command = zip_out.read(dir_file).decode("utf-8")
                return {"FINISHED"}
        else:
            self.report({'ERROR'}, "You need to select a .zip file")
            return {'CANCELLED'}
classes.append(AR_OT_ImportLoadSettings)

class AR_OT_Export(Operator, ExportHelper):
    bl_idname = "ar.data_export"
    bl_label = "Export"
    bl_description = "Export the Action file as a ZIP"

    filter_glob: StringProperty( default='*.zip', options={'HIDDEN'} )
    filename_ext = ".zip"
    filepath : StringProperty (name = "File Path", maxlen = 1024, default = "ActionRecorderButtons")
    allcats : BoolProperty(name= "All", description= "Export every Category")

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll)

    def execute(self, context):
        scene = context.scene
        temppath = bpy.app.tempdir + "AR_Zip"
        if not os.path.exists(temppath):
            os.mkdir(temppath)
        with zipfile.ZipFile(self.filepath, 'w') as zip_it:
            catindex = 0
            written = False
            for cat in scene.ar_filecategories:
                folderpath = os.path.join(temppath, f"{catindex}~" + cat.pn_name)
                if not os.path.exists(folderpath):
                    os.mkdir(folderpath)
                if cat.pn_selected or self.allcats:
                    written = True
                    for i in range(cat.FileDisp_Start, cat.FileDisp_Start + cat.FileDisp_length):
                        zip_path = os.path.join(folderpath, f"{i}~" + AR_Prop.FileDisp_Name[i] + ".py")
                        with open(zip_path, 'w', encoding='utf8') as recfile:
                            for cmd in AR_Prop.FileDisp_Command[i]:
                                recfile.write(cmd + '\n')
                        zip_it.write(zip_path, os.path.join(f"{catindex}~" + cat.pn_name, f"{i - cat.FileDisp_Start}~"+ AR_Prop.FileDisp_Name[i] + f"~{AR_Prop.FileDisp_Icon[i]}" + ".py"))
                        os.remove(zip_path)
                else:
                    index = 0
                    for i in range(cat.FileDisp_Start, cat.FileDisp_Start + cat.FileDisp_length):
                        if scene.ar_filedisp[i].Index:
                            written = True
                            zip_path = os.path.join(folderpath, f"{index}~" + AR_Prop.FileDisp_Name[i] + ".py")
                            with open(zip_path, 'w', encoding='utf8') as recfile:
                                for cmd in AR_Prop.FileDisp_Command[i]:
                                    recfile.write(cmd + '\n')
                            zip_it.write(zip_path, os.path.join(f"{catindex}~" + cat.pn_name, f"{index}~" + AR_Prop.FileDisp_Name[i] + f"~{AR_Prop.FileDisp_Icon[i]}" + ".py"))
                            os.remove(zip_path)
                            index += 1
                if written:
                    catindex += 1
                    written = False
                os.rmdir(folderpath)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box = layout.box()
        box.prop(self, 'allcats', text= "All")
        for cat in scene.ar_filecategories:
            box = layout.box()
            col = box.column()
            row = col.row()
            if cat.pn_show:
                row.prop(cat, 'pn_show', icon="TRIA_DOWN", text= "", emboss= False)
            else:
                row.prop(cat, 'pn_show', icon="TRIA_RIGHT", text= "", emboss= False)
            row.label(text= cat.pn_name)
            row.prop(cat, 'pn_selected', text= "")
            if cat.pn_show:
                col = box.column(align= False)
                if self.allcats or cat.pn_selected:
                    for i in range(cat.FileDisp_Start, cat.FileDisp_Start + cat.FileDisp_length):
                        col.label(text= AR_Prop.FileDisp_Name[i], icon= 'CHECKBOX_HLT')
                else:
                    for i in range(cat.FileDisp_Start, cat.FileDisp_Start + cat.FileDisp_length):
                        col.prop(scene.ar_filedisp[i], 'Index' , text= AR_Prop.FileDisp_Name[i])
    
    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        scene = context.scene
        scene.ar_filecategories.clear()
        for cat in AR_Var.Categories:
            new = scene.ar_filecategories.add()
            new.name = cat.name
            new.pn_name = cat.pn_name
            new.FileDisp_Start = cat.Instance_Start
            new.FileDisp_length = cat.Instance_length
        AR_Prop.FileDisp_Name.clear()
        AR_Prop.FileDisp_Command.clear()
        AR_Prop.FileDisp_Icon.clear()
        for inst in AR_Var.Instance_Coll:
            AR_Prop.FileDisp_Name.append(inst.name)
            AR_Prop.FileDisp_Icon.append(inst.icon)
            AR_Prop.FileDisp_Command.append([cmd.name for cmd in inst.command])
        scene.ar_filedisp.clear()
        for i in range(len(AR_Var.ar_enum)):
            scene.ar_filedisp.add()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
classes.append(AR_OT_Export)

class AR_OT_Record_Add(Operator):
    bl_idname = "ar.record_add"
    bl_label = "Add"
    bl_description = "Add a New Action"

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        Add(0)
        TempSave(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Record_Add)

class AR_OT_Record_Remove(Operator):
    bl_idname = "ar.record_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected Action"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        scene = context.scene
        Remove(0)
        TempUpdate()
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Record_Remove)

class AR_OT_Record_MoveUp(Operator):
    bl_idname = "ar.record_move_up"
    bl_label = "Move Up"
    bl_description = "Move the selected Action Up"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        scene = context.scene
        Move(0 , 'Up')
        TempUpdate()
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Record_MoveUp)

class AR_OT_Record_MoveDown(Operator):
    bl_idname = "ar.record_move_down"
    bl_label = "Move Down"
    bl_description = "Move the selected Action Down"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)
        
    def execute(self, context):
        scene = context.scene
        Move(0 , 'Down')
        TempUpdate()
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Record_MoveDown)

class AR_LLA_TextProps(PropertyGroup):
    name : StringProperty()
    apply : BoolProperty(default= False)
classes.append(AR_LLA_TextProps)

class AR_OT_Record_LoadLoaclActions(Operator):
    bl_idname = "ar.record_loadlocalactions"
    bl_label = "Load Loacl Actions"
    bl_description = "Load the Local Action from the last Save"

    Source : EnumProperty(name= 'Source', description= "Choose the source from where to load", items= [('scene', 'Scene', ''), ('text', 'Texteditor', '')])
    Texts : CollectionProperty(type= AR_LLA_TextProps)

    def execute(self, context):
        if self.Source == 'scene':
            LoadLocalActions(None)
        else:
            texts = []
            for text in self.Texts:
                if text.apply:
                    texts.append(text.name)
            LoadActionFromTexteditor(texts)
        TempUpdate()
        bpy.context.area.tag_redraw()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'Source', expand= True)
        if self.Source == 'text':
            box = layout.box()
            texts = [txt.name for txt in bpy.data.texts]
            for text in self.Texts:
                if text.name in texts:
                    row = box.row()
                    row.label(text= text.name)
                    row.prop(text, 'apply', text= '')

    def invoke(self, context, event):
        texts = self.Texts
        texts.clear()
        for text in bpy.data.texts:
            txt = texts.add()
            txt.name = text.name
        return bpy.context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_Record_LoadLoaclActions)

class AR_OT_Save(Operator):
    bl_idname = "ar.data_save"
    bl_label = "Save"
    bl_description = "Save all Global Actions to the Storage"

    def execute(self, context):
        Save()
        return {"FINISHED"}
classes.append(AR_OT_Save)

class AR_OT_Load(Operator):
    bl_idname = "ar.data_load"
    bl_label = "Load"
    bl_description = "Load all Action data from the Storage"

    def execute(self, context):
        Load()
        TempSaveCats()
        bpy.context.area.tag_redraw()
        return {"FINISHED"}
classes.append(AR_OT_Load)

class AR_OT_ButtonToRecord(Operator):
    bl_idname = "ar.category_button_to_record"
    bl_label = "Action Button to Local"
    bl_description = "Add the selected Action Button as a Local"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        
        Instance_to_Recorder()
        if AR_Var.BtnToRec_Mode == 'move':
            I_Remove()
            TempSaveCats()
            if AR_Var.Autosave:
                Save()
        TempUpdate()
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_ButtonToRecord)

class AR_OT_Button_Remove(Operator):
    bl_idname = "ar.category_remove_button"
    bl_label = "Remove Action Button"
    bl_description = "Remove the selected Action Button "

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        I_Remove()
        TempSaveCats()
        bpy.context.area.tag_redraw()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
classes.append(AR_OT_Button_Remove)

class AR_OT_Button_MoveUp(Operator):
    bl_idname = "ar.category_move_up_button"
    bl_label = "Move Button Up"
    bl_description = "Move the selected Action Button Up"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        I_Move('Up')
        TempSaveCats()
        bpy.context.area.tag_redraw()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Button_MoveUp)

class AR_OT_Button_MoveDown(Operator):
    bl_idname = "ar.category_move_down_button"
    bl_label = "Move Action Button Down"
    bl_description = "Move the selected Action Button Down"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll)
        
    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        I_Move('Down')
        TempSaveCats()
        bpy.context.area.tag_redraw()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Button_MoveDown)

class AR_OT_Button_Rename(Operator):
    bl_idname = "ar.category_rename_button"
    bl_label = "Rename Button"
    bl_description = "Rename the selected Button"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Instance_Coll) and not (multiselection_buttons[0] and len(InstanceLastselected) > 1)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        Rename_Instance()
        TempSaveCats()
        bpy.context.area.tag_redraw()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Button_Rename)

class AR_OT_Category_Cmd(Operator):
    bl_idname = 'ar.category_cmd_button'
    bl_label = 'ActRec Action Button'
    bl_description = 'Play this Action Button'
    bl_options = {'UNDO', 'INTERNAL'}

    Index : IntProperty()

    def execute(self, context):
        if Execute_Instance(self.Index):
            Data.alert_index = self.Index
            bpy.app.timers.register(AlertTimerCmd, first_interval = 1)
        return{'FINISHED'}
classes.append(AR_OT_Category_Cmd)

class IconTable(Operator):
    bl_label = "Icons"
    bl_description = "Press to select an Icon"

    def draw(self, execute):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text= "Selected Icon:")
        row.label(text=" ", icon_value= AR_Prop.SelectedIcon)
        row.prop(self, 'search', text= 'Search:')
        row.operator(AR_OT_Selector_Icon.bl_idname, text= "Clear Icon").icon = 101 #Icon: BLANK1
        box = layout.box()
        gridf = box.grid_flow(row_major=True, columns= 35, even_columns= True, even_rows= True, align= True)
        iconvalues = getIconsvalues()
        for i,ic in enumerate(getIcons()):
            normalname = ic.lower().replace("_"," ")
            if self.search == '' or self.search.lower() in normalname:
                gridf.operator(AR_OT_Selector_Icon.bl_idname, text= "", icon_value= iconvalues[i]).icon = iconvalues[i]
        box = layout.box()
        row = box.row().split(factor= 0.5)
        row.label(text= "Custom Icons")
        row2 = row.row()
        row2.operator(AR_OT_AddCustomIcon.bl_idname, text= "Add Custom Icon", icon= 'PLUS').activatPopUp = self.bl_idname
        row2.operator(AR_OT_DeleteCustomIcon.bl_idname, text= "Delete", icon= 'TRASH')
        gridf = box.grid_flow(row_major=True, columns= 35, even_columns= True, even_rows= True, align= True)
        customIconValues = [icon.icon_id for icon in preview_collections['ar_custom'].values()]
        for i,ic in enumerate(list(preview_collections['ar_custom'])):
            normalname = ic.lower().replace("_"," ")
            if self.search == '' or self.search.lower() in normalname:
                gridf.operator(AR_OT_Selector_Icon.bl_idname, text= "", icon_value= customIconValues[i]).icon = customIconValues[i]

    def check(self, context):
        return True

class AR_OT_Category_Cmd_Icon(IconTable, Operator):
    bl_idname = "ar.category_cmd_icon"

    notInit : BoolProperty(default=False)
    index : IntProperty()
    search : StringProperty(name= "Icon Search", description= "search Icon by name", options= {'TEXTEDIT_UPDATE'})

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Instance_Coll[self.index].icon = AR_Prop.SelectedIcon
        AR_Prop.SelectedIcon = 101 #Icon: BLANK1
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        bpy.context.area.tag_redraw()
        return {"FINISHED"}

    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Prop.SelectedIcon = AR_Var.Instance_Coll[self.index].icon
        self.search = ''
        return context.window_manager.invoke_props_dialog(self, width=1000)
classes.append(AR_OT_Category_Cmd_Icon)

class AR_OT_Selector_Icon(Operator):
    bl_idname = "ar.category_icon"
    bl_label = "Icon"
    bl_options = {'REGISTER','INTERNAL'}
    bl_description = "Select the Icon"

    icon : IntProperty(default= 101) #Icon: BLANK1

    def execute(self, context):
        AR_Prop.SelectedIcon = self.icon
        return {"FINISHED"}
classes.append(AR_OT_Selector_Icon)

class AR_OT_Record_SelectorUp(Operator):
    bl_idname = 'ar.record_selector_up'
    bl_label = 'ActRec Selection Up'

    def execute(self, context):
        Select_Command('Up')
        bpy.context.area.tag_redraw()
        return{'FINISHED'}
classes.append(AR_OT_Record_SelectorUp)

class AR_OT_Record_SelectorDown(Operator):
    bl_idname = 'ar.record_selector_down'
    bl_label = 'ActRec Selection Down'

    def execute(self, context):
        Select_Command('Down')
        bpy.context.area.tag_redraw()
        return{'FINISHED'}
classes.append(AR_OT_Record_SelectorDown)

class AR_OT_Record_Play(Operator):
    bl_idname = 'ar.record_play'
    bl_label = 'ActRec Play'
    bl_description = 'Play the selected Action.'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        index = AR_Var.Record_Coll[CheckCommand(0)].Index
        Play(AR_Var.Record_Coll[CheckCommand(index + 1)].Command, index)
        return{'FINISHED'}
classes.append(AR_OT_Record_Play)

class AR_OT_Record_Start(Operator):
    bl_idname = "ar.record_start"
    bl_label = "Start Recording"
    bl_description = "Starts Recording the Macros"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = bpy.context.scene
        Record(AR_Var.Record_Coll[CheckCommand(0)].Index + 1 , 'Start')
        bpy.context.area.tag_redraw()
        return {"FINISHED"}
classes.append(AR_OT_Record_Start)

class AR_OT_Record_Stop(Operator):
    bl_idname = "ar.record_stop"
    bl_label = "Stop Recording"
    bl_description = "Stops Recording the Macros"

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = bpy.context.scene
        messages = Record(AR_Var.Record_Coll[CheckCommand(0)].Index + 1 , 'Stop')
        if len(messages):
            mess = "\n    "
            for message in messages:
                mess += "%s \n    " %message
            self.report({'ERROR'}, "Not all actions were added because they are not of type Operator: %s" % mess)
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Record_Stop)

class AR_OT_Record_Icon(IconTable, Operator):
    bl_idname = "ar.record_icon"

    index : IntProperty()
    search : StringProperty(name= "Icon Search", description= "search Icon by name", options= {'TEXTEDIT_UPDATE'})

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Record_Coll[0].Command[self.index].icon = AR_Prop.SelectedIcon
        AR_Prop.SelectedIcon = 101 #Icon: BLANK1
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}

    def invoke(self, context, event):
        self.search = ''
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Prop.SelectedIcon = AR_Var.Record_Coll[0].Command[self.index].icon
        return context.window_manager.invoke_props_dialog(self, width=1000)
classes.append(AR_OT_Record_Icon)

class AR_OT_Record_Execute(Operator):
    bl_idname = "ar.record_execute"
    bl_label = "Execute Action"

    index : IntProperty()

    def execute(self, content):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        Play(AR_Var.Record_Coll[CheckCommand(self.index)].Command, self.index - 1)
        return {"FINISHED"}
classes.append(AR_OT_Record_Execute)

class AR_OT_Command_Add(Operator):
    bl_idname = "ar.command_add"
    bl_label = "ActRec Add Macro"
    bl_description = "Add the last operation you executed"

    command : StringProperty()

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        if self.command == "":
            message = Add(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        else:
            message = Add(AR_Var.Record_Coll[CheckCommand(0)].Index + 1, self.command)
        if message == "<Empty>":
            rec = AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)]
            index = len(rec.Command) - 1
            rec.Index = index
            bpy.ops.ar.command_edit('INVOKE_DEFAULT', index= index, Edit= True)
        elif type(message) == str:
            self.report({'ERROR'}, "Action could not be added because it is not of type Operator:\n %s" % message)
        elif message:
            self.report({'ERROR'}, "No Action could be added")
        if (AR_Var.CreateEmpty and message) or not message:
            rec = AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)]
            rec.Index = len(rec.Command) - 1
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Command_Add)

class AR_OT_Command_Remove(Operator):
    bl_idname = "ar.command_remove"
    bl_label = "Remove Macro"
    bl_description = "Remove the selected Macro"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        Remove(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Command_Remove)

class AR_OT_Command_MoveUp(Operator):
    bl_idname = "ar.command_move_up"
    bl_label = "Move Macro Up"
    bl_description = "Move the selected Macro up"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        Move(AR_Var.Record_Coll[CheckCommand(0)].Index + 1 , 'Up')
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Command_MoveUp)

class AR_OT_Command_MoveDown(Operator):
    bl_idname = "ar.command_move_down"
    bl_label = "Move Macro Down"
    bl_description = "Move the selected Macro down"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        Move(AR_Var.Record_Coll[CheckCommand(0)].Index + 1 , 'Down')
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Command_MoveDown)

class AR_OT_Command_Clear(Operator):
    bl_idname = "ar.command_clear"
    bl_label = "Clear Macros"
    bl_description = "Delete all Macro of the selected Action"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        Clear(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}
classes.append(AR_OT_Command_Clear)

def Edit_Commandupdate(self, context):
    Data.Edit_Command = self.Command
cmd_edit_time = [0]
class AR_OT_Command_Edit(Operator):
    bl_idname = "ar.command_edit"
    bl_label = "Edit"
    bl_description = "Double click to Edit"

    Name : StringProperty(name= "Name")
    Command : StringProperty(name= "Command", update= Edit_Commandupdate)
    last : StringProperty()
    index : IntProperty()
    Edit : BoolProperty(default= False)
    CopyData : BoolProperty(default= False, name= "Copy Previous", description= "Copy the data of the previous recorded Macro and place it in this Macro")

    def execute(self, context):
        self.Edit = False
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        index_btn = AR_Var.Record_Coll[CheckCommand(0)].Index + 1
        index_macro = AR_Var.Record_Coll[CheckCommand(index_btn)].Index
        macro = AR_Var.Record_Coll[CheckCommand(index_btn)].Command[index_macro]
        if self.CopyData:
            macro.macro = AR_Var.LastLine
            macro.cname = AR_Var.LastLineCmd
        else:
            macro.macro = self.Name
            macro.cname = self.Command
        TempUpdateCommand(index_btn)
        bpy.context.area.tag_redraw()
        SaveToDataHandler(None)
        return {"FINISHED"}

    def draw(self, context):
        self.Command = Data.Edit_Command
        AR_Var = context.preferences.addons[__package__].preferences
        layout = self.layout
        if self.CopyData:
            layout.prop(AR_Var, 'LastLine', text= "Name")
            layout.prop(AR_Var, 'LastLineCmd', text= "")
        else:
            layout.prop(self, 'Name', text= "Name")
            layout.prop(self, 'Command', text= "")
        row = layout.row().split(factor= 0.65)
        ops = row.operator(AR_OT_ClearOperator.bl_idname)
        ops.Command = self.Command
        row.prop(self, 'CopyData', toggle= True)

    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        index_btn = AR_Var.Record_Coll[CheckCommand(0)].Index + 1
        macro = AR_Var.Record_Coll[CheckCommand(index_btn)].Command[self.index]
        mlast = f"{index_btn}.{self.index}" 
        t = time.time()
        self.CopyData = False
        #print(str(self.last == mlast)+ "    " +str(cmd_edit_time[0] + 0.7 > t) + "      " + str(self.last) + "      " + str(mlast)+ "      " + str(cmd_edit_time[0])+ "      " + str(cmd_edit_time[0] + 0.7)+ "      " + str(t))
        if self.last == mlast and cmd_edit_time[0] + 0.7 > t or self.Edit:
            self.last = mlast
            cmd_edit_time[0] = t
            split = macro.cname.split(":")
            if split[0] == 'ar.event':
                data = json.loads(":".join(split[1:]))
                if data['Type'] == 'Timer':
                    bpy.ops.ar.addevent('INVOKE_DEFAULT', Type= data['Type'], Num= self.index, time= data['Time'])
                elif data['Type'] == 'Loop':
                    if data['StatementType'] == 'python':
                        bpy.ops.ar.addevent('INVOKE_DEFAULT', Type= data['Type'], Num= self.index, Statements= data['StatementType'], PythonStatement= data["PyStatement"])
                    else:
                        bpy.ops.ar.addevent('INVOKE_DEFAULT', Type= data['Type'], Num= self.index, Statements= data['StatementType'], Startnumber= data["Startnumber"], Endnumber= data["Endnumber"], Stepnumber= data["Stepnumber"])
                elif data['Type'] == 'Select Object':
                    bpy.ops.ar.addevent('INVOKE_DEFAULT', Type= data['Type'], Num= self.index, SelectedObject= data['Object'])
                elif data['Type'] == 'Select Vertices':
                    bpy.ops.ar.addevent('INVOKE_DEFAULT', Type= data['Type'], Num= self.index, VertObj= data['Object'])
                else:
                    bpy.ops.ar.addevent('INVOKE_DEFAULT', Type= data['Type'], Num= self.index)
                SaveToDataHandler(None)
                return {"FINISHED"}
            self.Name = macro.macro
            self.Command = macro.cname
            Data.Edit_Command = self.Command
            return context.window_manager.invoke_props_dialog(self, width=500)
        else:
            self.last = mlast
            cmd_edit_time[0] = t
            AR_Var.Record_Coll[CheckCommand(index_btn)].Index = self.index
        return {"FINISHED"}

    def cancel(self, context):
        self.Edit = False
classes.append(AR_OT_Command_Edit)

class AR_OT_Command_Run_Queued(Operator):
    bl_idname = "ar.command_run_queued"
    bl_label = "Run Queued Commands"
    bl_options ={'INTERNAL'}

    _timer = None

    def execute(self, context):
        while not execution_queue.empty():
            function = execution_queue.get()
            function()
            Data.ActiveTimers -= 1
        return {"FINISHED"}
    
    def modal(self, context, event):
        if Data.ActiveTimers > 0:
            self.execute(context)
            return {'PASS_THROUGH'}
        else:
            self.cancel(context)
            return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
classes.append(AR_OT_Command_Run_Queued)

class AR_OT_AddEvent(Operator):
    bl_idname = "ar.addevent"
    bl_label = "Add Event"
    bl_description = "Add a Event which wait until the Event is Triggered"

    TypesList = [('Timer', 'Timer', 'Wait the chosen Time and continue with the Macros', 'SORTTIME', 0),
                ('Render Complet', 'Render complet', 'Wait until the rendering has finished', 'IMAGE_RGB_ALPHA', 1),
                ('Render Init', 'Render Init', 'Wait until the rendering has started', 'IMAGE_RGB', 2),
                ('Loop', 'Loop', 'Loop the conatining Makros until the Statment is False \nNote: The Loop need the EndLoop Event to work, otherwise the Event get skipped', 'FILE_REFRESH', 3),
                ('EndLoop', 'EndLoop', 'Ending the latetest called loop, when no Loop Event was called this Event get skipped', 'FILE_REFRESH', 4),
                ('Clipboard', 'Clipboard', 'Adding a command with the data from the Clipboard', 'CONSOLE', 5),
                ('Empty', 'Empty', 'Crates an Empty Macro', 'SHADING_BBOX', 6) #,
                #('Select Object', 'Select Object', 'Select the choosen object', 'OBJECT_DATA', 7),
                #('Select Vertices', 'Select Vertices', 'Select the choosen verts', 'GROUP_VERTEX', 8)
                ]
    Type : EnumProperty(items= TypesList, name= "Event Type", description= 'Shows all possible Events', default= 'Timer')
    time : FloatProperty(name= "Time", description= "Time in Seconds", unit='TIME')
    Statements : EnumProperty(items=[('count', 'Count', 'Count a Number from the Startnumber with the Stepnumber to the Endnumber, \nStop when Number > Endnumber', '', 0),
                                    ('python', 'Python Statment', 'Create a custom statement with python code', '', 1)])
    Startnumber : FloatProperty(name= "Startnumber", description= "Startnumber of the Count statements", default=0)
    Stepnumber : FloatProperty(name= "Stepnumber", description= "Stepnumber of the Count statements", default= 1)
    Endnumber : FloatProperty(name= "Endnumber", description= "Endnumber of the Count statements", default= 1)
    PythonStatement : StringProperty(name= "Statement", description= "Statment for the Python Statement")
    Num : IntProperty(default= -1)
    SelectedObject : StringProperty(name= "Object", description= "Choose an Object which get select when this Event is played")
    VertObj : StringProperty(name= "Object", description= "Choose an Object to get the selected verts from")

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        if self.Num == -1:
            Item = AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command.add()
        else:
            Item = AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command[self.Num]
        if self.Type == 'Clipboard':
            cmd = context.window_manager.clipboard
            macro = GetMacro(cmd)
            if type(macro) != str:
                macro = cmd
            Item.macro = macro
            Item.cname = cmd
        elif self.Type == 'Empty':
            Item.macro = "<Empty>"
            Item.cname = ""
        else:
            Item.macro = "Event: " + self.Type
            data = {'Type': self.Type}
            if self.Type == 'Timer':
                data['Time'] = self.time
            elif self.Type == 'Loop':
                data['StatementType'] = self.Statements
                if self.Statements == 'python':
                    data["PyStatement"] = self.PythonStatement
                else:
                    data["Startnumber"] = self.Startnumber
                    data["Endnumber"] = self.Endnumber
                    data["Stepnumber"] = self.Stepnumber
            elif self.Type == 'Select Object':
                data['Object'] = self.SelectedObject
            elif self.Type == 'Select Vertices':
                data['Object'] = self.VertObj
                selverts = []
                obj = bpy.context.view_layer.objects[self.VertObj]
                obj.update_from_editmode()
                verts = obj.data.vertices
                for v in verts:
                    if v.select:
                        selverts.append(v.index)
                data['Verts'] = selverts
            Item.cname = "ar.event:" + json.dumps(data)
        rec = AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)]
        rec.Index = len(rec.Command) - 1
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'Type')
        if self.Type == 'Timer':
            box = layout.box()
            box.prop(self, 'time')
        elif self.Type == 'Loop':
            box = layout.box()
            box.prop(self, 'Statements')
            box.separator()
            if self.Statements == 'python':
                box.prop(self, 'PythonStatement')
            else:
                box.prop(self, 'Startnumber')
                box.prop(self, 'Endnumber')
                box.prop(self, 'Stepnumber')
        elif self.Type == 'Select Object':
            box = layout.box()
            box.prop_search(self, 'SelectedObject', bpy.context.view_layer, 'objects')
        elif self.Type == 'Select Vertices':
            box = layout.box()
            box.prop_search(self, 'VertObj', bpy.data, 'meshes')

    def invoke(self, context, event):
        if bpy.context.object != None:
            obj = bpy.context.object.name
            self.SelectedObject = obj
            index = bpy.data.meshes.find(obj)
            if index != -1:
                self.VertObj = obj
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_AddEvent)

class AR_OT_CopyToActRec(Operator):
    bl_idname = "ar.copy_to_actrec"
    bl_label = "Copy to Action Recorder"
    bl_description = "Copy the selected Operator to Action Recorder Macro"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return context.active_object is not None and len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        bpy.ops.ui.copy_python_command_button()
        bpy.ops.ar.command_add('EXEC_DEFAULT', command= bpy.context.window_manager.clipboard)
        return {"FINISHED"}
classes.append(AR_OT_CopyToActRec)

class AR_OT_ClearOperator(Operator):
    bl_idname = "ar.command_clearoperator"
    bl_label = "Clear Operator"
    bl_options = {'INTERNAL'}

    Command : StringProperty()
    
    def execute(self, context):
        Data.Edit_Command = self.Command.split("(")[0] + "()"
        return {"FINISHED"}
classes.append(AR_OT_ClearOperator)

class AR_OT_Preferences_DirectorySelector(Operator, ExportHelper):
    bl_idname = "ar.preferences_directoryselector"
    bl_label = "Select Directory"
    bl_description = " "
    bl_options = {'REGISTER','INTERNAL'}

    filename_ext = "."
    use_filter_folder = True
    filepath : StringProperty (name = "File Path", maxlen = 0, default = " ")

    directory : StringProperty()

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        userpath = self.properties.filepath
        if(not os.path.isdir(userpath)):
            msg = "Please select a directory not a file\n" + userpath
            self.report({'ERROR'}, msg)
            return{'CANCELLED'}
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.StorageFilePath = os.path.join(userpath, self.directory)
        return{'FINISHED'}
classes.append(AR_OT_Preferences_DirectorySelector)

class AR_OT_Preferences_RecoverDirectory(Operator):
    bl_idname = "ar.preferences_recoverdirectory"
    bl_label = "Recover Standart Directory"
    bl_description = "Recover the standart Storage directory"
    bl_options = {'REGISTER','INTERNAL'}

    directory : StringProperty()

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.StorageFilePath = os.path.join(os.path.dirname(__file__), self.directory)
        return{'FINISHED'}
classes.append(AR_OT_Preferences_RecoverDirectory)

class AR_OT_Help_OpenURL(Operator):
    bl_idname = "ar.help_openurl"
    bl_label = "Open URL"
    bl_description = " "

    url : StringProperty()

    def execute(self, context):
        webbrowser.open(self.url)
        return {"FINISHED"}
classes.append(AR_OT_Help_OpenURL)

class AR_OT_CheckUpdate(Operator):
    bl_idname = "ar.check_update"
    bl_label = "Check for Update"
    bl_description = "check for available update"

    def execute(self, context):
        update = CheckForUpdate()
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Update = update[0]
        if isinstance(update[1], str):
            AR_Var.Version = update[1]
        else:
            AR_Var.Version = ".".join([str(i) for i in update[1]])
        return {"FINISHED"}
classes.append(AR_OT_CheckUpdate)

class AR_OT_Update(Operator):
    bl_idname = "ar.update"
    bl_label = "Update"
    bl_description = "install the new version"

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        AR_Var.Update = False
        AR_Var.Restart = True
        Update()
        bpy.ops.ar.restart('INVOKE_DEFAULT')
        return {"FINISHED"}
classes.append(AR_OT_Update)

class AR_OT_ReleaseNotes(Operator):
    bl_idname = "ar.releasenotes"
    bl_label = "Releas Notes"
    bl_description = "open the Releas Notes in the Web-Browser"

    def execute(self, context):
        webbrowser.open(config['releasNotes_URL'])
        return {"FINISHED"}
classes.append(AR_OT_ReleaseNotes)

class AR_OT_Restart(Operator):
    bl_idname = "ar.restart"
    bl_label = "Restart Blender"
    bl_description = "Restart Blender"

    def execute(self, context):
        path = bpy.data.filepath
        if path == '':
            os.startfile(bpy.app.binary_path)
        else:
            bpy.ops.wm.save_mainfile(filepath= path)
            os.startfile(path)
        bpy.ops.wm.quit_blender()
        return {"FINISHED"}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text= "You need to restart Blender to complete the Update")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_Restart)

class AR_OT_CheckCtrl(Operator):
    bl_idname = "ar.check_ctrl"
    bl_label = "Check Ctrl"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        multiselection_buttons[0] = event.ctrl
        return {"FINISHED"}
classes.append(AR_OT_CheckCtrl)

class AR_OT_AddCustomIcon(Operator, ImportHelper):
    bl_idname = "ar.add_customicon"
    bl_label = "Add Custom Icon"
    bl_description = "Adds a custom Icon"

    filter_glob : StringProperty(default='*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp', options={'HIDDEN'} )
    activatPopUp : StringProperty(default= "")

    def execute(self, context):
        if os.path.isfile(self.filepath) and self.filepath.lower().endswith(('.png','.jpg','.jpeg','.tif','.tiff','.bmp')):
            err = LoadIcons(self.filepath)
            if err is not None:
                self.report({'ERROR'}, err)
        else:
            self.report({'ERROR'}, 'The selected File is not an Image')
        if self.activatPopUp != "":
            exec("bpy.ops." + ".".join(self.activatPopUp.split("_OT_")).lower() + "('INVOKE_DEFAULT')")
        return {"FINISHED"}
classes.append(AR_OT_AddCustomIcon)

class AR_OT_DeleteCustomIcon(Operator):
    bl_idname = "ar.deletecustomicon"
    bl_label = "Delete Icon"
    bl_description = "Delete a custom added icon"

    class AR_Icon(PropertyGroup):
        iconId : IntProperty()
        iconName : StringProperty()
        select : BoolProperty(default= False, name= 'Select')
    classes.append(AR_Icon)
    IconsColl : CollectionProperty(type= AR_Icon)
    AllIcons : BoolProperty(name= "All Icons", description= "Select all Icons")

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        for ele in self.IconsColl:
            if ele.select or self.AllIcons:
                iconpath = ele.iconName[3:]
                filenames = os.listdir(AR_Var.IconFilePath)
                names = [os.path.splitext(os.path.basename(path))[0] for path in filenames]
                if iconpath in names:
                    os.remove(os.path.join(AR_Var.IconFilePath,  filenames[names.index(iconpath)]))
                unregisterIcon(preview_collections['ar_custom'], ele.iconName)
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'AllIcons')
        box = layout.box()
        coll = self.IconsColl
        if self.AllIcons:
            for ele in coll:
                row = box.row()
                row.label(text= '', icon= "CHECKBOX_HLT")
                row.label(text= ele.iconName[3:], icon_value= ele.iconId)
        else:
            for ele in coll:
                row = box.row()
                row.prop(ele, 'select', text= '')
                row.label(text= ele.iconName[3:], icon_value= ele.iconId)

    def invoke(self, context, event):
        coll = self.IconsColl
        coll.clear()
        iconl = list(preview_collections['ar_custom'])
        iconl_v = [icon.icon_id for icon in preview_collections['ar_custom'].values()]
        for i in range(len(iconl)):
            new = coll.add()
            new.iconId = iconl_v[i]
            new.iconName = iconl[i]
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_DeleteCustomIcon)
# endregion

# region Menus
class AR_MT_Action_Pie(Menu):
    bl_idname = "view3d.menuname"
    bl_label = "ActRec Pie Menu"
    bl_idname = "AR_MT_Action_Pie"

    def draw(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        pie = self.layout.menu_pie()
        actions = AR_Var.Record_Coll[CheckCommand(0)].Command
        for i in range(len(actions)):
            if i >= 8:
                break
            ops = pie.operator(AR_OT_Record_Execute.bl_idname, text= actions[i].cname).index = i + 1
classes.append(AR_MT_Action_Pie)

def menu_func(self, context):
    if bpy.ops.ui.copy_python_command_button.poll():
        layout = self.layout
        layout.separator()
        layout.operator(AR_OT_CopyToActRec.bl_idname)

class WM_MT_button_context(Menu):
    bl_label = "Add Viddyoze Tag"

    def draw(self, context):
        pass
classes.append(WM_MT_button_context)

# endregion

# region PropertyGroups
def SavePrefs(self, context):
    if not ontempload[0]:
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        TempUpdateCommand(AR_Var.Record_Coll[0].Index + 1)

def SetRecordName(self, value):
    textI = bpy.data.texts.find(self.cname)
    if textI != -1:
        text = bpy.data.texts[textI]
        text.name = value
    self['cname'] = value
    SaveToDataHandler(None)

def GetCname(self):
    return self.get('cname', '')

class AR_Record_Struct(PropertyGroup):
    cname : StringProperty(set= SetRecordName, get=GetCname) #AR_Var.name
    macro : StringProperty()
    active : BoolProperty(default= True, update= SavePrefs, description= 'Toggles Macro on and off.')
    alert : BoolProperty()
    icon : IntProperty(default= 286) #Icon: MESH_PLANE
classes.append(AR_Record_Struct)

class AR_Record_Merge(PropertyGroup):
    Index : IntProperty()
    Command : CollectionProperty(type = AR_Record_Struct)
classes.append(AR_Record_Merge)

currentselected = [None]
lastselected = [0]
def UseRadioButtons(self, context):
    AR_Var = context.preferences.addons[__package__].preferences
    categories = AR_Var.Categories
    index = GetPanelIndex(self)
    if self.pn_selected and currentselected[0] != index:
        currentselected[0] = index
        if lastselected[0] != index and lastselected[0] < len(categories):
            categories[lastselected[0]].pn_selected = False
        lastselected[0] = index
    elif not self.pn_selected and index == lastselected[0] and currentselected[0] == index:
        self.pn_selected = True

class AR_CategorizeProps(PropertyGroup):
    pn_name : StringProperty()
    pn_show : BoolProperty(default= True)
    pn_selected : BoolProperty(default= False, update= UseRadioButtons)
    Instance_Start : IntProperty(default= 0)
    Instance_length : IntProperty(default= 0)
classes.append(AR_CategorizeProps)

InstanceCurrentselected = [None]
InstanceLastselected = [0]
def Instance_Updater(self, context):
    if oninit[0]:
        return
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    enum = AR_Var.ar_enum
    if multiselection_buttons[1]:
        bpy.ops.ar.check_ctrl('INVOKE_DEFAULT')
    if multiselection_buttons[0]:
        if self.Value:
            if not self.Index in InstanceLastselected:
                InstanceLastselected.insert(0, self.Index)
                AR_Var.Instance_Index = self.Index
        else:
            InstanceLastselected.remove(self.Index)
            if len(InstanceLastselected) < 1:
                self.Value = True
        InstanceCurrentselected[0] = self.Index
    else:
        if len(InstanceLastselected) > 1:
            lastcopy = InstanceLastselected[:]
            InstanceLastselected.clear()
            InstanceLastselected.append(0)
            for lasti in lastcopy:
                if lasti == self.Index:
                    self.Value = True
                else:
                    enum[lasti].Value = False
        if self.Value and InstanceCurrentselected[0] != self.Index:
            InstanceCurrentselected[0] = self.Index
            if InstanceLastselected[0] != self.Index and InstanceLastselected[0] < len(enum):
                enum[InstanceLastselected[0]].Value = False
            InstanceLastselected[0] = self.Index
            AR_Var.Instance_Index = self.Index
        if not self.Value and InstanceLastselected[0] == self.Index and InstanceCurrentselected[0] == self.Index:
            self.Value = True

class AR_Enum(PropertyGroup):
    Value : BoolProperty(default= False, update= Instance_Updater, description= "Select this Action Button", name = 'Select')
    Index : IntProperty()
    Init = True
classes.append(AR_Enum)

class AR_FileDisp(PropertyGroup):
    Index : BoolProperty(default= False)
classes.append(AR_FileDisp)

class AR_CategorizeFileDisp(PropertyGroup):
    pn_name : StringProperty()
    pn_show : BoolProperty(default= True)
    pn_selected : BoolProperty(default= False)
    FileDisp_Start : IntProperty(default= 0)
    FileDisp_length : IntProperty(default= 0)
classes.append(AR_CategorizeFileDisp)

class AR_CommandString(PropertyGroup):
    name : StringProperty()
classes.append(AR_CommandString)

class AR_Struct(PropertyGroup):
    name: StringProperty()
    command: CollectionProperty(type= AR_CommandString)
    icon : IntProperty(default= 101) #Icon BLANK1
classes.append(AR_Struct)

class AR_ImportButton(PropertyGroup):
    btn_name: StringProperty()
    icon: StringProperty()
    command: StringProperty()
    enum: EnumProperty(items= [("add", "Add", ""),("overwrite", "Overwrite", "")], name= "Import Mode")
classes.append(AR_ImportButton)

class AR_ImportCategory(PropertyGroup):
    cat_name: StringProperty()
    Buttons : CollectionProperty(type= AR_ImportButton)
    enum: EnumProperty(items= [("new", "New", "Create a new Category"),("append", "Append", "Append to an existing Category")], name= "Import Mode")
    show : BoolProperty(default= True)
classes.append(AR_ImportCategory)

categoryCurrentselected = [None]
categoryLastselected = [0]
def CategoriesRadioButton(self, content):
    index = self.index
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    radioCats = AR_Var.Selected_Category
    if self.selected and categoryCurrentselected[0] != index:
        categoryCurrentselected[0] = index
        if categoryLastselected[0] != index and categoryLastselected[0] < len(radioCats):
            radioCats[categoryLastselected[0]].selected = False
        categoryLastselected[0] = index
    elif not self.selected and index == categoryLastselected[0] and categoryCurrentselected[0] == index:
        self.selected = True

class AR_SelectedCategory(PropertyGroup):
    selected : BoolProperty(update= CategoriesRadioButton, description= 'Select this Category', name= 'Select')
    index : IntProperty()
classes.append(AR_SelectedCategory)

class AR_CommandEditProp(PropertyGroup):
    prop : bpy.types.Property
# endregion

class AR_Prop(AddonPreferences):
    bl_idname = __package__

    Rename : StringProperty()
    Autosave : BoolProperty(default= True, name= "Autosave", description= "automatically saves all Global Buttons to the Storage")
    RecToBtn_Mode : EnumProperty(items=[("copy", "Copy", "Copy the Action over to Global"), ("move", "Move", "Move the Action over to Global and Delete it from Local")], name= "Mode")
    BtnToRec_Mode : EnumProperty(items=[("copy", "Copy", "Copy the Action over to Local"), ("move", "Move", "Move the Action over to Local and Delete it from Global")], name= "Mode")
    SelectedIcon = 101 # Icon: BLANK1

    Instance_Coll : CollectionProperty(type= AR_Struct)
    Instance_Index : IntProperty(default= 0)
    ar_enum : CollectionProperty(type= AR_Enum)

    Categories : CollectionProperty(type= AR_CategorizeProps)
    Selected_Category : CollectionProperty(type= AR_SelectedCategory)
    ShowAllCategories : BoolProperty(name= "Show All Categories", default= False)

    FileDisp_Name = []
    FileDisp_Command = []
    FileDisp_Icon = []
    FileDisp_Index : IntProperty(default= 0)

    HideMenu : BoolProperty(name= "Hide Menu", description= "Hide Menu")
    ShowMacros : BoolProperty(name= "Show Macros" ,description= "Show Macros", default= True)

    Record = False
    Temp_Command = []
    Temp_Num = 0

    Record_Coll : CollectionProperty(type= AR_Record_Merge)
    CreateEmpty : BoolProperty(default= True)
    LastLineIndex : IntProperty()
    LastLine : StringProperty(default= "<Empty>")
    LastLineCmd : StringProperty()

    StorageFilePath : StringProperty(name= "Stroage Path", description= "The Path to the Storage for the saved Categories", default= os.path.join(os.path.dirname(__file__), "Storage"))
    IconFilePath : StringProperty(name= "Icon Path", description= "The Path to the Storage for the added Icons", default= os.path.join(os.path.dirname(__file__), "Icons"))

    Importsettings : CollectionProperty(type= AR_ImportCategory)
    Update : BoolProperty()
    Version : StringProperty()
    Restart : BoolProperty()
    AutoUpdate : BoolProperty(default= True, name= "Auto Update", description= "automatically search for a new Update")
    ShowKeymap : BoolProperty(default= True)
    # (Operator.bl_idname, key, event, Ctrl, Alt, Shift)
    addon_keymaps = []
    key_assign_list = \
    [
    (AR_OT_Command_Add.bl_idname, 'COMMA', 'PRESS', False, False, True, None),
    (AR_OT_Record_Play.bl_idname, 'PERIOD', 'PRESS', False, False, True, None),
    (AR_OT_Record_SelectorUp.bl_idname, 'WHEELUPMOUSE','PRESS', False, False, True, None),
    (AR_OT_Record_SelectorDown.bl_idname, 'WHEELDOWNMOUSE','PRESS', False, False, True, None),
    ("wm.call_menu_pie", 'A', 'PRESS', False, True, True, AR_MT_Action_Pie.bl_idname),
    ]

    def draw(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        layout = self.layout
        col = layout.column()
        row = col.row()
        if AR_Var.Update:
            row.operator(AR_OT_Update.bl_idname, text= "Update")
            row.operator(AR_OT_ReleaseNotes.bl_idname, text= "Release Notes")
        else:
            row.operator(AR_OT_CheckUpdate.bl_idname, text= "Check For Updates")
            if AR_Var.Restart:
                row.operator(AR_OT_Restart.bl_idname, text= "Restart to Finsih")
        if AR_Var.Version != '':
            if AR_Var.Update:
                col.label(text= "A new Version is available (" + AR_Var.Version + ")")
            else:
                col.label(text= "You are using the latest Vesion (" + AR_Var.Version + ")")
        col.separator(factor= 1.5)
        col.label(text= 'Action Storage Folder')
        row = col.row()
        row.operator(AR_OT_Preferences_DirectorySelector.bl_idname, text= "Select Action Button’s Storage Folder", icon= 'FILEBROWSER').directory = "Storage"
        row.operator(AR_OT_Preferences_RecoverDirectory.bl_idname, text= "Recover Default Folder", icon= 'FOLDER_REDIRECT').directory = "Storage"
        box = col.box()
        box.label(text= self.StorageFilePath)
        col.separator(factor= 1.5)
        row = col.row().split(factor= 0.5)
        row.label(text= "Icon Storage Folder")
        row2 = row.row(align= True).split(factor= 0.65, align= True)
        row2.operator(AR_OT_AddCustomIcon.bl_idname, text= "Add Custom Icon", icon= 'PLUS')
        row2.operator(AR_OT_DeleteCustomIcon.bl_idname, text= "Delete", icon= 'TRASH')
        row = col.row()
        row.operator(AR_OT_Preferences_DirectorySelector.bl_idname, text= "Select Icon Storage Folder", icon= 'FILEBROWSER').directory = "Icons"
        row.operator(AR_OT_Preferences_RecoverDirectory.bl_idname, text= "Recover Default Folder", icon= 'FOLDER_REDIRECT').directory = "Icons"
        box = col.box()
        box.label(text= self.IconFilePath)
        col.separator(factor= 1.5)
        box = col.box()
        row = box.row()
        row.prop(self, "ShowKeymap", text= "", icon= 'TRIA_DOWN' if self.ShowKeymap else 'TRIA_RIGHT', emboss= False)
        row.label(text="Keymap")
        if self.ShowKeymap:
            wm = bpy.context.window_manager
            kc = wm.keyconfigs.user
            km = kc.keymaps['Screen']
            for (idname, key, event, ctrl, alt, shift, name) in AR_Prop.key_assign_list:
                kmi = km.keymap_items[idname]
                rna_keymap_ui.draw_kmi([], kc, km, kmi, box, 0)
classes.append(AR_Prop)

# region Registration
spaceTypes = ["VIEW_3D", "IMAGE_EDITOR", "NODE_EDITOR", "SEQUENCE_EDITOR", "CLIP_EDITOR", "DOPESHEET_EDITOR", "GRAPH_EDITOR", "NLA_EDITOR", "TEXT_EDITOR"]
for spaceType in spaceTypes:
    panelFactory( spaceType )

def Initialize_Props():
    bpy.types.Scene.ar_filecategories = CollectionProperty(type= AR_CategorizeFileDisp)
    bpy.types.Scene.ar_filedisp = CollectionProperty(type= AR_FileDisp)
    bpy.types.Scene.ar_local = StringProperty(name= 'AR Local', description= 'Scene Backup-Data of AddonPreference.RecordColl (= Local Actions)', default= '{}')
    bpy.app.handlers.depsgraph_update_pre.append(InitSavedPanel)
    bpy.app.handlers.undo_post.append(TempLoad) # add TempLoad to ActionHandler and call ist after undo
    bpy.app.handlers.redo_post.append(TempLoad) # also for redo
    bpy.app.handlers.undo_post.append(TempLoadCats)
    bpy.app.handlers.redo_post.append(TempLoadCats)
    bpy.app.handlers.save_pre.append(SaveToDataHandler)
    bpy.app.handlers.load_post.append(LoadLocalActions)
    bpy.app.handlers.render_complete.append(runRenderComplete)
    bpy.app.handlers.render_init.append(runRenderInit)
    bpy.types.WM_MT_button_context.append(menu_func)
    if bpy.context.window_manager.keyconfigs.addon:
        km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name='Screen')
        AR_Prop.addon_keymaps.append(km)
        for (idname, key, event, ctrl, alt, shift, name) in AR_Prop.key_assign_list:
            kmi = km.keymap_items.new(idname, key, event, ctrl=ctrl, alt=alt, shift=shift)
            if not name is None:
                kmi.properties.name = name
    pcoll = bpy.utils.previews.new()
    preview_collections['ar_custom'] = pcoll
    bpy.app.timers.register(TimerInitSavedPanel, first_interval = 1)

def Clear_Props():
    del bpy.types.Scene.ar_filedisp
    del bpy.types.Scene.ar_filecategories
    del bpy.types.Scene.ar_local
    bpy.app.handlers.undo_post.remove(TempLoad)
    bpy.app.handlers.redo_post.remove(TempLoad)
    bpy.app.handlers.undo_post.remove(TempLoadCats)
    bpy.app.handlers.redo_post.remove(TempLoadCats)
    bpy.app.handlers.save_pre.remove(SaveToDataHandler)
    bpy.app.handlers.load_post.remove(LoadLocalActions)
    try:
        bpy.app.handlers.render_complete.remove(runRenderComplete)
    except:
        print("runRenderComplete")
    try:
        bpy.app.handlers.render_init.remove(runRenderInit)
    except:
        print("runRenderInit")
    try:
        bpy.types.WM_MT_button_context.remove(menu_func)
    except:
        print('menu_func')
    try:
        bpy.app.handlers.depsgraph_update_pre.remove(InitSavedPanel)
    except:
        pass
    bpy.context.window_manager.keyconfigs.addon.keymaps.remove(AR_Prop.addon_keymaps[0])
    AR_Prop.addon_keymaps.clear() #Unregister Preview Collection
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
# endregion

#================================================
# The region commentaries use the extension “#region folding for VS Code” 
#================================================
