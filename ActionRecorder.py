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
from .IconList import Icons as IconList
from .config import config
import atexit
from urllib import request
from io import BytesIO
from . import __init__ as init
import base64

from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import Panel, UIList, Operator, PropertyGroup, AddonPreferences
from bpy_extras.io_utils import ImportHelper, ExportHelper

classes = []
classespanel = []
categoriesclasses = []
catlength = [0]
activeareas = []
ontempload = [False]


# UIList ======================================================================================
class AR_UL_Selector(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        self.use_filter_show = False
        self.use_filter_sort_lock = True
        row = layout.row(align= True)
        row.alert = item.alert
        row.operator(AR_OT_Record_Icon.bl_idname, text= "", icon= AR_Var.Record_Coll[0].Command[index].icon, emboss= False).index = index
        row.operator(AR_OT_Record_Edit.bl_idname, text= item.cname, emboss= False).index = index
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

# Functions =====================================================================================
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
        return eval(name.split("(")[0] + ".get_rna_type().name")
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
        for i in range (AR_Prop.Temp_Num, len(Recent)):
            TempText = Recent[i-1].body
            if TempText.count('bpy'):
                name = TempText[TempText.find('bpy'):]
                macro = GetMacro(name)
                if macro is None or macro is True:
                    notadded.append(name)
                    if macro is None and AR_Var.CreateEmpty:
                        Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                else:
                    Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                    Item.macro = macro
                    Item.cname = name
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

def Add(Num):
    Recent = Get_Recent('Reports_All')
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if Num:
        try: #Add Macro
            if Recent[-2].body.count('bpy'):
                Name_Temp = Recent[-2].body
                name = Name_Temp[Name_Temp.find('bpy'):]
                macro = GetMacro(name)
                if macro is True:
                    Name_Temp = Recent[-3].body
                    name = Name_Temp[Name_Temp.find('bpy'):]
                    macro = GetMacro(name)

            else:
                Name_Temp = Recent[-3].body
                name = Name_Temp[Name_Temp.find('bpy'):]
                macro = GetMacro(name)
                if macro is True:
                    Name_Temp = Recent[-4].body
                    name = Name_Temp[Name_Temp.find('bpy'):]
                    macro = GetMacro(name)
            notadded = False
            if macro is None or macro is True:
                notadded = name
                if macro is None and AR_Var.CreateEmpty:
                    Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
            else:
                Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
                Item.macro = macro
                Item.cname = name
            UpdateRecordText(Num)
            bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
            return notadded
        except:
            bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
            return True
    else: # Add Record
        Item = AR_Var.Record_Coll[CheckCommand(Num)].Command.add()
        Item.cname = CheckForDublicates([cmd.cname for cmd in AR_Var.Record_Coll[CheckCommand(0)].Command], 'Untitled.001')
        bpy.data.texts.remove(bpy.data.texts['Recent Reports'])
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

def Play(Commands): #Execute the Macro
    for Command in Commands:
        if Command.active:
            try:
                exec(Command.cname)
            except:
                Command.alert = True
                return True # Alert

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
            with open(os.path.join(panelpath, f"{cmd_i - start}~" + AR_Var.Instance_Coll[cmd_i].name + "~" + AR_Var.Instance_Coll[cmd_i].icon + ".py"), 'w', encoding='utf8') as cmd_file:
                for cmd in AR_Var.Instance_Coll[cmd_i].command:
                    cmd_file.write(cmd.name + "\n")

def Load():#Load Buttons from Storage
    print('------------------Load-----------------')
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    for cat in AR_Var.Categories:
        RegisterUnregister_Category(GetPanelIndex(cat), False)
    AR_Var.Categories.clear()
    scene.ar_enum.clear()
    AR_Var.Instance_Coll.clear()
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
                new_e = scene.ar_enum.add()
                e_index = len(scene.ar_enum) - 1
                new_e.name = str(e_index)
                new_e.Index = e_index
            for txt in textfiles:
                sortedtxt[int(txt.split('~')[0])] = txt #get the index 
            for i in range(len(sortedtxt)):
                txt = sortedtxt[i]
                inst = AR_Var.Instance_Coll.add()
                inst.name = "".join(txt.split('~')[1:-1])
                inst.icon = os.path.splitext(txt)[0].split('~')[-1]
                CmdList = []
                with open(os.path.join(folderpath, txt), 'r', encoding='utf8') as text:
                    for line in text.readlines():
                        cmd = inst.command.add()
                        cmd.name = line.strip()
    SetEnumIndex()
    
def Recorder_to_Instance(panel): #Convert Record to Button
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    i = panel.Instance_Start +  panel.Instance_length
    data = {"name":CheckForDublicates([ele.name for ele in AR_Var.Instance_Coll], AR_Var.Record_Coll[CheckCommand(0)].Command[AR_Var.Record_Coll[CheckCommand(0)].Index].cname),
            "command": [Command.cname for Command in AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command],
            "icon": AR_Var.Record_Coll[CheckCommand(0)].Command[AR_Var.Record_Coll[CheckCommand(0)].Index].icon}
    Inst_Coll_Insert(i, data , AR_Var.Instance_Coll)
    panel.Instance_length += 1
    new_e = scene.ar_enum.add()
    e_index = len(scene.ar_enum) - 1
    new_e.name = str(e_index)
    new_e.Index = e_index
    p_i = GetPanelIndex(panel)
    categories = AR_Var.Categories
    if p_i < len(categories):
        for cat in categories[ p_i + 1: ]:
            cat.Instance_Start += 1

def Instance_to_Recorder():#Convert Button to Record
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    Item = AR_Var.Record_Coll[CheckCommand(0)].Command.add()
    Item.cname = AR_Var.Instance_Coll[AR_Var.Instance_Index].name
    Item.icon = AR_Var.Instance_Coll[AR_Var.Instance_Index].icon
    for Command in AR_Var.Instance_Coll[AR_Var.Instance_Index].command:
        Item = AR_Var.Record_Coll[CheckCommand(len(AR_Var.Record_Coll[CheckCommand(0)].Command))].Command.add()
        Item.macro = GetMacro(Command.name)
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
    if len(AR_Var.Instance_Coll) :
        Index = AR_Var.Instance_Index
        AR_Var.Instance_Coll.remove(Index)
        scene.ar_enum.remove(len(scene.ar_enum) - 1)
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
    SetEnumIndex()

def I_Move(Mode): # Move a Button to the upper/lower
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    index1 = AR_Var.Instance_Index
    if Mode == 'Up' :
        index2 = AR_Var.Instance_Index - 1
    else :
        index2 = AR_Var.Instance_Index + 1
    LengthTemp = len(AR_Var.Instance_Coll)
    if (2 <= LengthTemp) and (0 <= index1 < LengthTemp) and (0 <= index2 <LengthTemp):
        AR_Var.Instance_Coll[index1].name , AR_Var.Instance_Coll[index2].name = AR_Var.Instance_Coll[index2].name , AR_Var.Instance_Coll[index1].name
        AR_Var.Instance_Coll[index1].icon , AR_Var.Instance_Coll[index2].icon = AR_Var.Instance_Coll[index2].icon , AR_Var.Instance_Coll[index1].icon
        index1cmd = [cmd.name for cmd in AR_Var.Instance_Coll[index1].command]
        index2cmd = [cmd.name for cmd in AR_Var.Instance_Coll[index2].command]
        AR_Var.Instance_Coll[index1].command.clear()
        AR_Var.Instance_Coll[index2].command.clear()
        for cmd in index1cmd:
            new = AR_Var.Instance_Coll[index1].command.add()
            new.name = cmd
        for cmd in index2cmd:
            new = AR_Var.Instance_Coll[index2].command.add()
            new.name = cmd
        scene.ar_enum[index2].Value = True

#Initalize Standert Button List
@persistent
def InitSavedPanel(dummy = None):
    try:
        bpy.app.timers.unregister(InitSavedPanel)
        bpy.app.handlers.depsgraph_update_pre.remove(InitSavedPanel)
    except:
        print("Already Loaded")
        return
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    if bpy.data.filepath == '':
        AR_Var.Record_Coll.clear()
    AR_Var.Update = False
    AR_Var.Version = ''
    AR_Var.Restart = False
    if not os.path.exists(AR_Var.StorageFilePath):
        os.mkdir(AR_Var.StorageFilePath)
    Load()
    catlength[0] = len(AR_Var.Categories)
    TempSaveCats()
    TempUpdate()

def GetPanelIndex(cat): #Get Index of a Category
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    return AR_Var.Categories.find(cat.name)

def SetEnumIndex(): #Set enum, if out of range to the first enum
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    scene = bpy.context.scene
    if len(scene.ar_enum):
        enumIndex = AR_Var.Instance_Index * (AR_Var.Instance_Index < len(scene.ar_enum))
        scene.ar_enum[enumIndex].Value = True
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
    scene.ar_enum.clear()
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
            new_e = scene.ar_enum.add()
            new_e.name = str(i)
            new_e.Index = i
        scene.ar_enum[index].Value = True
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

def AlertTimerPlay(): #Remove alert after time passed for Recored
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    btnlist = AR_Var.Record_Coll[CheckCommand(0)].Command
    for i in range(len(btnlist)):
        if btnlist[i].alert:
            btnlist[i].alert = False
            for ele in AR_Var.Record_Coll[CheckCommand(i + 1)].Command:
                if ele.alert:
                    ele.alert = False
                    for area in activeareas:
                        for i in classespanel:
                            if i.__name__ == "AR_PT_Local_" + area or i.__name__ == "AR_PT_MacroEditer_" + area:
                                bpy.utils.unregister_class(i)
                                bpy.utils.register_class(i)
                    return 

def AlertTimerCmd(): #Remove alert after time passed for Buttons
    alert_index[0] = None

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
    collection[index].icon = data["icon"]
    collection[index].command.clear()
    for command in data["command"]:
        cmd = collection[index].command.add()
        cmd.name = command

def SaveToPrefs():
    if bpy.data.filepath != '':
        bpy.ops.wm.save_userpref()

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
            new_i = int(dirlist[i].split("~")[0])
            sorteddirlist[new_i] = dirlist[i]
            dirfileslist[new_i], dirfileslist[i] = dirfileslist[i], dirfileslist[new_i]
            sortedfilelist = [None] * len(dirfileslist[new_i])
            for fil in dirfileslist[new_i]:
                sortedfilelist[int(os.path.basename(fil).split("~")[0])] = fil
            dirfileslist[new_i] = sortedfilelist
        return (dirfileslist, sorteddirlist)

def CheckForUpdate():
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
                        if updateVersion[0] > currentVersion[0] or updateVersion[1] > currentVersion[1] or updateVersion[2] > currentVersion[2]:
                            return (True, updateVersion)
                        else:
                            return (False, currentVersion)

def GetVersion(line):
    return eval("(%s)" %line.split("(")[1].split(")")[0])

def Update():
    source = request.urlopen(config["repoSource_URL"] + "/archive/master.zip")
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

# Panels ===================================================================================
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
        #メニューの描画処理
        def draw(self, context):
            AR_Var = context.preferences.addons[__package__].preferences
            scene = bpy.context.scene
            layout = self.layout
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
                col.enabled = len(AR_Var.Instance_Coll) > 0
                col.prop(AR_Var , 'Rename' , text='')
                row2.operator(AR_OT_Button_Rename.bl_idname , text='Rename')
    AR_PT_Global.__name__ = "AR_PT_Global_%s" % spaceType
    classes.append(AR_PT_Global)

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
            layout.operator(AR_OT_Help_OpenURL.bl_idname, text= "Manual", icon= 'ASSET_MANAGER').url = config["Manual_URL"]
            layout.operator(AR_OT_Help_OpenURL.bl_idname, text= "Hint", icon= 'HELP').url = config["Hint_URL"]
            layout.operator(AR_OT_Help_OpenURL.bl_idname, text= "Bug Report", icon= 'URL').url = config["BugReport_URL"]
    AR_PT_Help.__name__ = "AR_PT_Help_%s" % spaceType
    classes.append(AR_PT_Help)

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
            col.operator(AR_OT_Category_Add.bl_idname, text= 'Add')
            col.operator(AR_OT_Category_Rename.bl_idname, text= 'Rename')
            col.operator(AR_OT_Category_Delet.bl_idname, text= 'Remove')
            col.label(text= "Data Management", icon= 'FILE_FOLDER')
            col.operator(AR_OT_Import.bl_idname, text= 'Import')
            col.operator(AR_OT_Export.bl_idname, text= 'Export')
            col.label(text= "Strage File Settings", icon= "FOLDER_REDIRECT")
            row = col.row()
            row.label(text= "AutoSave")
            row.prop(AR_Var, 'Autosave', toggle= True, text= "On" if AR_Var.Autosave else "Off")
            col.operator(AR_OT_Save.bl_idname , text='Save to File' )
            col.operator(AR_OT_Load.bl_idname , text='Load from File' )
            col.label(text= "Local Settings")
            col.prop(AR_Var, 'CreateEmpty', text= "Create Empty Macro on Error")
    AR_PT_Advanced.__name__ = "AR_PT_Advanced_%s" % spaceType
    classes.append(AR_PT_Advanced)

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

            def draw_header(self, context):
                AR_Var = context.preferences.addons[__package__].preferences
                index = int(self.bl_idname.split("_")[3])
                category = AR_Var.Categories[index]
                layout = self.layout
                row = layout.row()
                row.alignment = 'LEFT'
                row.label(text= category.pn_name)
                row2 = row.row(align= True)
                row2.operator(AR_OT_Category_MoveUp.bl_idname, icon="TRIA_UP", text= "").Index = index
                row2.operator(AR_OT_Category_MoveDown.bl_idname, icon="TRIA_DOWN", text="").Index = index

            def draw(self, context):
                AR_Var = context.preferences.addons[__package__].preferences
                scene = context.scene
                index = int(self.bl_idname.split("_")[3])
                category = AR_Var.Categories[index]
                layout = self.layout
                col = layout.column()
                for i in range(category.Instance_Start, category.Instance_Start + category.Instance_length):
                    row = col.row(align=True)
                    row.alert = alert_index[0] == i
                    row.prop(scene.ar_enum[i], 'Value' ,toggle = 1, icon= 'LAYER_ACTIVE' if scene.ar_enum[i].Value else 'LAYER_USED', text= "")
                    row.operator(AR_OT_Category_Cmd_Icon.bl_idname, text= "", icon= AR_Var.Instance_Coll[i].icon).index = i
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

# Opertators ===============================================================================
class AR_OT_Category_Add(Operator):
    bl_idname = "ar.category_add"
    bl_label = "Add Category"

    Name : StringProperty(name = "Name", default="")

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        scene = context.scene
        new = AR_Var.Categories.add()
        name = CheckForDublicates([n.pn_name for n in AR_Var.Categories], self.Name)
        new.name = name
        new.pn_name = name
        new.Instance_Start = len(AR_Var.Instance_Coll)
        new.Instance_length = 0
        bpy.context.area.tag_redraw()
        TempSaveCats()
        RegisterUnregister_Category(GetPanelIndex(new))
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'Name')         
classes.append(AR_OT_Category_Add)

class AR_OT_Category_Delet(Operator):
    bl_idname = "ar.category_delet"
    bl_label = "Delet Category"
    bl_description = "Delete the selected Category"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Categories)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        scene = context.scene
        for cat in categories:
            if cat.pn_selected:
                index = GetPanelIndex(cat)
                start = cat.Instance_Start
                for i in range(start, start + cat.Instance_length):
                    scene.ar_enum.remove(len(scene.ar_enum) - 1)
                    AR_Var.Instance_Coll.remove(start)
                for nextcat in categories[index + 1 :]:
                    nextcat.Instance_Start -= cat.Instance_length
                categories.remove(index)
                RegisterUnregister_Category(len(categories), False)
                SetEnumIndex()
                break
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
    
    def draw(self, context):    
        AR_Var = context.preferences.addons[__package__].preferences    
        layout = self.layout
        categories = AR_Var.Categories
        for cat in categories:
            layout.prop(cat, 'pn_selected', text= cat.pn_name)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_Category_Delet)

class AR_OT_Category_Rename(Operator):
    bl_idname = "ar.category_rename"
    bl_label = "Rename Category"
    bl_description = "Rename the selected Category"

    PanelName : StringProperty(name = "New Name", default="")

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Categories)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        for cat in categories:
            if cat.pn_selected:
                cat.name = self.PanelName
                cat.pn_name = self.PanelName
                break
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}

    def draw(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        layout = self.layout
        categories = AR_Var.Categories
        for cat in categories:
            layout.prop(cat, 'pn_selected', text= cat.pn_name)
        layout.prop(self, 'PanelName')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_Category_Rename)

class AR_OT_Category_MoveButton(Operator):
    bl_idname = "ar.category_move_category_button"
    bl_label = "Move Button"
    bl_description = "Moves the selected Button of a Category to another Category"

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
                Index = AR_Var.Instance_Index
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
                Inst_Coll_Insert(catendl -1 * (Index < catendl), data, AR_Var.Instance_Coll)
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
        if i - 1 >= 0:
            cat1 = categories[i]
            cat2 = categories[i - 1]
            cat1.name, cat2.name = cat2.name, cat1.name
            cat1.pn_name, cat2.pn_name = cat2.pn_name, cat1.pn_name
            cat1.pn_show, cat2.pn_show = cat2.pn_show, cat1.pn_show
            cat1.pn_selected, cat2.pn_selected = cat2.pn_selected, cat1.pn_selected
            cat1.Instance_Start, cat2.Instance_Start = cat2.Instance_Start, cat1.Instance_Start
            cat1.Instance_length, cat2.Instance_length = cat2.Instance_length, cat1.Instance_length
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
        if i + 1 < len(categories):
            cat1 = categories[i]
            cat2 = categories[i + 1]
            cat1.name, cat2.name = cat2.name, cat1.name
            cat1.pn_name, cat2.pn_name = cat2.pn_name, cat1.pn_name
            cat1.pn_show, cat2.pn_show = cat2.pn_show, cat1.pn_show
            cat1.pn_selected, cat2.pn_selected = cat2.pn_selected, cat1.pn_selected
            cat1.Instance_Start, cat2.Instance_Start = cat2.Instance_Start, cat1.Instance_Start
            cat1.Instance_length, cat2.Instance_length = cat2.Instance_length, cat1.Instance_length
        bpy.context.area.tag_redraw()
        TempSaveCats()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Category_MoveDown)

class AR_OT_RecordToButton(Operator):
    bl_idname = "ar.record_record_to_button"
    bl_label = "Record to Button"
    bl_description = "Add the selectd Record to a Category"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
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

    def draw(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        categories = AR_Var.Categories
        layout = self.layout
        for cat in categories:
            layout.prop(cat, 'pn_selected', text= cat.pn_name)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
classes.append(AR_OT_RecordToButton)

class AR_OT_Import(Operator, ImportHelper):
    bl_idname = "ar.data_import"
    bl_label = "Import"

    filter_glob: StringProperty( default='*.zip', options={'HIDDEN'} )

    Category : StringProperty(default= "Imports")
    AddNewCategory : BoolProperty(default= False)
    Mode : EnumProperty(name= 'Mode', items= [("add","Add",""),("overwrite", "Overwrite", "")])

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        scene = context.scene
        ar_categories = AR_Var.Categories
        if self.filepath.endswith(".zip"):
            if self.Mode == 'overwrite':
                dirfileslist, sorteddirlist = ImportSortedZip(self.filepath)
                for cat in ar_categories:
                    RegisterUnregister_Category(len(categories), False)
                ar_categories.clear()
                AR_Var.Instance_Coll.clear()
                AR_Var.Instance_Index = 0
                scene.ar_enum()
                with zipfile.ZipFile(self.filepath, 'r') as zip_out:
                    for i in range(len(sorteddirlist)):
                        cat = AR_Var.Importsettings.add()
                        name = "".join(sorteddirlist[i].split("~")[1:])
                        cat.pn_name = name
                        cat.name = name
                        cat.Instance_Start = len(AR_Var.Instance_Coll)
                        RegisterUnregister_Category(GetPanelIndex(cat))
                        for dir_file in dirfileslist[i]:
                            btn = AR_Var.Instance_Coll.add()
                            name_icon = os.path.splitext(os.path.basename(dir_file))[0]
                            btn.name = "".join(name_icon.split("~")[1:-1])
                            btn.icon = name_icon.split("~")[-1]
                            for cmd in zip_out.read(dir_file).decode("utf-8").splitlines():
                                new = btn.command.add()
                                new.name = cmd
                    TempSaveCats()
            else:
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
                                icon = name_icon.split("~")[-1]
                                inst = AR_Var.Instance_Coll.add()
                                inst.name = CheckForDublicates([ele.name for ele in AR_Var.Instance_Coll], name)
                                inst.icon = icon
                                for line in zip_out.read(btn_file).decode("utf-8").splitlines():
                                    cmd = inst.command.add()
                                    cmd.name = line
                                new_e = scene.ar_enum.add()
                                e_index = len(scene.ar_enum) - 1
                                new_e.name = str(e_index)
                                new_e.Index = e_index
                                mycat.Instance_length += 1
                else:
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
                                            inst.icon = btn.icon
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
                            data = {"name": CheckForDublicates([ele.name for ele in AR_Var.Instance_Coll], name),
                                    "command": btn.command.splitlines(),
                                    "icon": icon}
                            Inst_Coll_Insert(inserti, data, AR_Var.Instance_Coll)
                            new_e = scene.ar_enum.add()
                            e_index = len(scene.ar_enum) - 1
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

class AR_OT_ImportLoadSettings(bpy.types.Operator):
    bl_idname = "ar.data_import_options"
    bl_label = "Load Importsettings"
    bl_description = "Load the select the file to change the importsettings"

    filepath : StringProperty()

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        if os.path.exists(self.filepath) and self.filepath.endswith(".zip"):
            dirfileslist, sorteddirlist = ImportSortedZip(self.filepath)
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
        for i in range(len(scene.ar_enum)):
            scene.ar_filedisp.add()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
classes.append(AR_OT_Export)

class AR_OT_Record_Add(Operator):
    bl_idname = "ar.record_add"
    bl_label = "Add"
    bl_description = "Add a new Record"

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        Add(0)
        TempSave(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Record_Add)

class AR_OT_Record_Remove(Operator):
    bl_idname = "ar.record_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected Record"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        scene = context.scene
        Remove(0)
        TempUpdate()
        bpy.context.area.tag_redraw()
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Record_Remove)

class AR_OT_Record_MoveUp(Operator):
    bl_idname = "ar.record_move_up"
    bl_label = "Move Up"
    bl_description = "Move the selected Record up"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        scene = context.scene
        Move(0 , 'Up')
        TempUpdate()
        bpy.context.area.tag_redraw()
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Record_MoveUp)

class AR_OT_Record_MoveDown(Operator):
    bl_idname = "ar.record_move_down"
    bl_label = "Move Down"
    bl_description = "Move the selected Record down"
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
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Record_MoveDown)

class AR_OT_Save(Operator):
    bl_idname = "ar.data_save"
    bl_label = "Save"
    bl_description = "Save all data to the disk (delete the old data from the disk)"

    def execute(self, context):
        Save()
        return {"FINISHED"}
classes.append(AR_OT_Save)

class AR_OT_Load(Operator):
    bl_idname = "ar.data_load"
    bl_label = "Load"
    bl_description = "Load all data from the disk (delete the current data in Blender)"

    def execute(self, context):
        Load()
        TempSaveCats()
        bpy.context.area.tag_redraw()
        return {"FINISHED"}
classes.append(AR_OT_Load)

class AR_OT_ButtonToRecord(Operator):
    bl_idname = "ar.category_button_to_record"
    bl_label = "Button to Record"
    bl_description = "Load the selected Button as a Record"

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
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_ButtonToRecord)

class AR_OT_Button_Remove(Operator):
    bl_idname = "ar.category_remove_button"
    bl_label = "Remove Button"
    bl_description = "Remove the selected Button"

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
    bl_description = "Move the selected Button up"

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
    bl_label = "Move Button Down"
    bl_description = "Move the selected Button down"

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
        return len(AR_Var.Instance_Coll)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        Rename_Instance()
        TempSaveCats()
        bpy.context.area.tag_redraw()
        if AR_Var.Autosave:
            Save()
        return {"FINISHED"}
classes.append(AR_OT_Button_Rename)

alert_index = [None]
class AR_OT_Category_Cmd(Operator):
    bl_idname = 'ar.category_cmd_button'
    bl_label = 'ComRec Command'
    bl_options = {'UNDO', 'INTERNAL'}

    Index : IntProperty()

    def execute(self, context):
        if Execute_Instance(self.Index):
            alert_index[0] = self.Index
            bpy.app.timers.register(AlertTimerCmd, first_interval = 1)
        return{'FINISHED'}
classes.append(AR_OT_Category_Cmd)

class AR_OT_Category_Cmd_Icon(bpy.types.Operator):
    bl_idname = "ar.category_cmd_icon"
    bl_label = "Icons"
    bl_description = "Press to select an Icon"

    index : IntProperty()

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Instance_Coll[self.index].icon = AR_Prop.SelectedIcon
        AR_Prop.SelectedIcon = "BLANK1"
        bpy.context.area.tag_redraw()
        return {"FINISHED"}
    
    def draw(self, execute):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text= "Selected Icon:")
        row.label(text=" ", icon= AR_Prop.SelectedIcon)
        row.operator(AR_OT_Selector_Icon.bl_idname, text= "Clear Icon").icon = "BLANK1"
        box = layout.box()
        gridf = box.grid_flow(row_major=True, columns= 35, even_columns= True,  even_rows= True, align= True)
        for ic in IconList:
            gridf.operator(AR_OT_Selector_Icon.bl_idname, text= "", icon= ic).icon = ic

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=1000)
classes.append(AR_OT_Category_Cmd_Icon)

class AR_OT_Selector_Icon(Operator):
    bl_idname = "ar.category_icon"
    bl_label = "Icon"
    bl_options = {'REGISTER','INTERNAL'}

    icon : StringProperty(default= "BLANK1")

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
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)].Command)

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        index = AR_Var.Record_Coll[CheckCommand(0)].Index
        alert = Play(AR_Var.Record_Coll[CheckCommand(index + 1)].Command)
        if alert:
            AR_Var.Record_Coll[CheckCommand(0)].Command[index].alert = True
            bpy.app.timers.register(AlertTimerPlay, first_interval = 1)
            activeareas.clear()
            for area in context.screen.areas:
                if area.type in spaceTypes:
                    activeareas.append(area.type)
            bpy.context.area.tag_redraw()
        return{'FINISHED'}
classes.append(AR_OT_Record_Play)

class AR_OT_Record_Start(Operator):
    bl_idname = "ar.record_start"
    bl_label = "Start Recording"
    bl_description = "starts recording the actions"

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
    bl_description = "stops recording the actions"

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
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Record_Stop)

class AR_OT_Record_Icon(bpy.types.Operator):
    bl_idname = "ar.record_icon"
    bl_label = "Icons"
    bl_description = "Press to select an Icon"

    index : IntProperty()

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Record_Coll[0].Command[self.index].icon = AR_Prop.SelectedIcon
        AR_Prop.SelectedIcon = "BLANK1"
        bpy.context.area.tag_redraw()
        SaveToPrefs()
        return {"FINISHED"}
    
    def draw(self, execute):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text= "Selected Icon:")
        row.label(text=" ", icon= AR_Prop.SelectedIcon)
        row.operator(AR_OT_Selector_Icon.bl_idname, text= "Clear Icon").icon = "BLANK1"
        box = layout.box()
        gridf = box.grid_flow(row_major=True, columns= 35, even_columns= True,  even_rows= True, align= True)
        for ic in IconList:
            gridf.operator(AR_OT_Selector_Icon.bl_idname, text= "", icon= ic).icon = ic

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=1000)
classes.append(AR_OT_Record_Icon)

class AR_OT_Command_Add(Operator):
    bl_idname = "ar.command_add"
    bl_label = "ActRec Add Macro"
    bl_description = "Add a Macro to the selected Record"

    @classmethod
    def poll(cls, context):
        AR_Var = context.preferences.addons[__package__].preferences
        return len(AR_Var.Record_Coll[CheckCommand(0)].Command)

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        message = Add(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        if type(message) == str:
            self.report({'ERROR'}, "Action could not be added because it is not of type Operator:\n %s" % message)
        elif message:
            self.report({'ERROR'}, "No Action could be added")
        TempUpdateCommand(AR_Var.Record_Coll[CheckCommand(0)].Index + 1)
        bpy.context.area.tag_redraw()
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Command_Add)

class AR_OT_Command_Remove(Operator):
    bl_idname = "ar.command_remove"
    bl_label = "Remove Command"
    bl_description = "Remove the selected Command"

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
        SaveToPrefs()
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
        SaveToPrefs()
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
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Command_MoveDown)

class AR_OT_Command_Clear(Operator):
    bl_idname = "ar.command_clear"
    bl_label = "Clear Command"
    bl_description = "Delete all Commands of the selected Record"

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
        SaveToPrefs()
        return {"FINISHED"}
classes.append(AR_OT_Command_Clear)

cmd_edit_time = [0]
class AR_OT_Command_Edit(bpy.types.Operator):
    bl_idname = "ar.command_edit"
    bl_label = "Edit"
    bl_description = "Double click to Edit"

    Name : StringProperty(name= "Name")
    Command : StringProperty(name= "Command")
    last : StringProperty()
    index : IntProperty()

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        index_btn = AR_Var.Record_Coll[CheckCommand(0)].Index + 1
        index_macro = AR_Var.Record_Coll[CheckCommand(index_btn)].Index
        macro = AR_Var.Record_Coll[CheckCommand(index_btn)].Command[index_macro]
        macro.macro = self.Name
        macro.cname = self.Command
        TempUpdateCommand(index_btn)
        bpy.context.area.tag_redraw()
        SaveToPrefs()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'Name', text= "Name")
        layout.prop(self, 'Command', text= "")

    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        index_btn = AR_Var.Record_Coll[CheckCommand(0)].Index + 1
        macro = AR_Var.Record_Coll[CheckCommand(index_btn)].Command[self.index]
        mlast = f"{index_btn}.{self.index}" 
        t = time.time()
        #print(str(self.last == mlast)+ "    " +str(cmd_edit_time[0] + 0.7 > t) + "      " + str(self.last) + "      " + str(mlast)+ "      " + str(cmd_edit_time[0])+ "      " + str(cmd_edit_time[0] + 0.7)+ "      " + str(t))
        if self.last == mlast and cmd_edit_time[0] + 0.7 > t:
            self.last = mlast
            cmd_edit_time[0] = t
            self.Name = macro.macro
            self.Command = macro.cname
            return context.window_manager.invoke_props_dialog(self, width=500)
        else:
            self.last = mlast
            cmd_edit_time[0] = t
            AR_Var.Record_Coll[CheckCommand(index_btn)].Index = self.index
        return {"FINISHED"}
classes.append(AR_OT_Command_Edit)

rec_edit_time = [0]
class AR_OT_Record_Edit(bpy.types.Operator):
    bl_idname = "ar.record_edit"
    bl_label = "Edit"
    bl_description = "Double Click to Edit"

    Name : StringProperty(name= "Name")
    last : StringProperty()
    index : IntProperty()

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        index_btn = AR_Var.Record_Coll[CheckCommand(0)].Index
        record = AR_Var.Record_Coll[CheckCommand(0)].Command[index_btn]
        record.cname = self.Name
        TempUpdateCommand(index_btn)
        bpy.context.area.tag_redraw()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'Name', text= "Name")

    def invoke(self, context, event):
        AR_Var = context.preferences.addons[__package__].preferences
        index_btn = AR_Var.Record_Coll[CheckCommand(0)].Index
        record =  AR_Var.Record_Coll[CheckCommand(0)].Command[index_btn]
        mlast = f"{index_btn}"
        t = time.time()
        if self.last == mlast and rec_edit_time[0] + 0.7 > t:
            self.last = mlast
            rec_edit_time[0] = t
            self.Name = record.cname
            return context.window_manager.invoke_props_dialog(self, width=200)
        else:
            self.last = mlast
            rec_edit_time[0] = t
            AR_Var.Record_Coll[CheckCommand(0)].Index = self.index
        return {"FINISHED"}
classes.append(AR_OT_Record_Edit)

class AR_OT_Preferences_DirectorySelector(Operator, ExportHelper):
    bl_idname = "ar.preferences_directoryselector"
    bl_label = "Select Directory"
    bl_description = " "
    bl_options = {'REGISTER','INTERNAL'}

    filename_ext = "."
    use_filter_folder = True
    filepath : StringProperty (name = "File Path", maxlen = 0, default = "")

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        userpath = self.properties.filepath
        if(not os.path.isdir(userpath)):
            msg = "Please select a directory not a file\n" + userpath
            self.report({'ERROR'}, msg)
            return{'CANCELLED'}
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.StorageFilePath = os.path.join(userpath, "Storage")
        return{'FINISHED'}
classes.append(AR_OT_Preferences_DirectorySelector)

class AR_OT_Preferences_RecoverDirectory(Operator):
    bl_idname = "ar.preferences_recoverdirectory"
    bl_label = "Recover Standart Directory"
    bl_description = "Recover the standart Storage directory"
    bl_options = {'REGISTER','INTERNAL'}

    def execute(self, context):
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.StorageFilePath = os.path.join(os.path.dirname(__file__), "Storage")
        return{'FINISHED'}
classes.append(AR_OT_Preferences_RecoverDirectory)

class AR_OT_Help_OpenURL(bpy.types.Operator):
    bl_idname = "ar.help_openurl"
    bl_label = "Open URL"
    bl_description = " "

    url : StringProperty()

    def execute(self, context):
        webbrowser.open(self.url)
        return {"FINISHED"}
classes.append(AR_OT_Help_OpenURL)

class AR_OT_CheckUpdate(bpy.types.Operator):
    bl_idname = "ar.check_update"
    bl_label = "Check for Update"
    bl_description = "check for available update"

    def execute(self, context):
        update = CheckForUpdate()
        AR_Var = context.preferences.addons[__package__].preferences
        AR_Var.Update = update[0]
        AR_Var.Version = ".".join([str(i) for i in update[1]])
        return {"FINISHED"}
classes.append(AR_OT_CheckUpdate)

class AR_OT_Update(bpy.types.Operator):
    bl_idname = "ar.update"
    bl_label = "Update"
    bl_description = "install the new version"

    def execute(self, context):
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        AR_Var.Update = False
        AR_Var.Restart = True
        Update()
        return {"FINISHED"}
classes.append(AR_OT_Update)

class AR_OT_ReleaseNotes(bpy.types.Operator):
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
classes.append(AR_OT_Restart)

# PropertyGroups =======================================================================
def SavePrefs(self, context):
    if not ontempload[0]:
        AR_Var = bpy.context.preferences.addons[__package__].preferences
        SaveToPrefs()
        TempUpdateCommand(AR_Var.Record_Coll[0].Index + 1)
    
class AR_Record_Struct(PropertyGroup):
    cname : StringProperty() #AR_Var.name
    macro : StringProperty()
    active : BoolProperty(default= True, update= SavePrefs)
    alert : BoolProperty()
    icon : StringProperty(default= 'BLANK1')
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
    AR_Var = bpy.context.preferences.addons[__package__].preferences
    enum = context.scene.ar_enum
    if self.Value and InstanceCurrentselected[0] != self.Index:
        InstanceCurrentselected[0] = self.Index
        if InstanceLastselected[0] != self.Index and InstanceLastselected[0] < len(enum):
            enum[InstanceLastselected[0]].Value = False
        InstanceLastselected[0] = self.Index
        AR_Var.Instance_Index = self.Index
    if not self.Value and InstanceLastselected[0] == self.Index and InstanceCurrentselected[0] == self.Index:
        self.Value = True

class AR_Enum(PropertyGroup):
    Value : BoolProperty(default= False, update= Instance_Updater)
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
    icon : StringProperty(default= 'BLANK1')
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

class AR_Prop(AddonPreferences):#何かとプロパティを収納
    bl_idname = __package__

    Rename : StringProperty() #AR_Var.name
    Autosave : BoolProperty(default= True, name= "Autosave", description= "automatically saves all Global Buttons to the Storage")
    RecToBtn_Mode : EnumProperty(items=[("copy", "Copy", "Copy the Action over to Global"), ("move", "Move", "Move the Action over to Global and delete it from Local")], name= "Mode")
    BtnToRec_Mode : EnumProperty(items=[("copy", "Copy", "Copy the Action over to Local"), ("move", "Move", "Move the Action over to local and delete it from Global")], name= "Mode")
    SelectedIcon = "BLANK1"

    Instance_Coll : CollectionProperty(type= AR_Struct)
    Instance_Index : IntProperty(default= 0)

    Categories : CollectionProperty(type= AR_CategorizeProps)

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
    CreateEmpty : BoolProperty()

    StorageFilePath : StringProperty(name= "Stroage Path", description= "The Path to the Storage for the saved Categories", default= os.path.join(os.path.dirname(__file__), "Storage"))

    Importsettings : CollectionProperty(type= AR_ImportCategory)
    Update : BoolProperty()
    Version : StringProperty()
    Restart : BoolProperty()

    # (Operator.bl_idname, key, event, Ctrl, Alt, Shift)
    addon_keymaps = []
    key_assign_list = \
    [
    (AR_OT_Command_Add.bl_idname, 'COMMA', 'PRESS', False, False, True),
    (AR_OT_Record_Play.bl_idname, 'PERIOD', 'PRESS', False, False, True),
    (AR_OT_Record_SelectorUp.bl_idname, 'WHEELUPMOUSE','PRESS', False, False, True),
    (AR_OT_Record_SelectorDown.bl_idname, 'WHEELDOWNMOUSE','PRESS', False, False, True)
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
        row = col.row()
        row.operator(AR_OT_Preferences_DirectorySelector.bl_idname, text= "Select Strage Folder", icon= 'FILEBROWSER')
        row.operator(AR_OT_Preferences_RecoverDirectory.bl_idname, text= "Recover Default Directory", icon= 'FOLDER_REDIRECT')
        box = col.box()
        box.label(text= self.StorageFilePath)
classes.append(AR_Prop)

# Registration ================================================================================================
spaceTypes = ["VIEW_3D", "IMAGE_EDITOR", "NODE_EDITOR", "SEQUENCE_EDITOR", "CLIP_EDITOR", "DOPESHEET_EDITOR", "GRAPH_EDITOR", "NLA_EDITOR", "TEXT_EDITOR"]
for spaceType in spaceTypes:
    panelFactory( spaceType )

def Initialize_Props():# プロパティをセットする関数
    bpy.types.Scene.ar_enum = CollectionProperty(type= AR_Enum)
    bpy.types.Scene.ar_filecategories = CollectionProperty(type= AR_CategorizeFileDisp)
    bpy.types.Scene.ar_filedisp = CollectionProperty(type= AR_FileDisp)
    bpy.app.handlers.depsgraph_update_pre.append(InitSavedPanel)
    bpy.app.handlers.undo_post.append(TempLoad) # add TempLoad to ActionHandler and call ist after undo
    bpy.app.handlers.redo_post.append(TempLoad) # also for redo
    bpy.app.handlers.undo_post.append(TempLoadCats)
    bpy.app.handlers.redo_post.append(TempLoadCats)
    if bpy.context.window_manager.keyconfigs.addon:
        km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name='Window', space_type='EMPTY')
        AR_Prop.addon_keymaps.append(km)
        for (idname, key, event, ctrl, alt, shift) in AR_Prop.key_assign_list:
            kmi = km.keymap_items.new(idname, key, event, ctrl=ctrl, alt=alt, shift=shift)
    bpy.app.timers.register(InitSavedPanel, first_interval = 2.5)

def Clear_Props():
    del bpy.types.Scene.ar_enum
    del bpy.types.Scene.ar_filedisp
    del bpy.types.Scene.ar_filecategories
    bpy.app.handlers.undo_post.remove(TempLoad)
    bpy.app.handlers.redo_post.remove(TempLoad)
    bpy.app.handlers.undo_post.remove(TempLoadCats)
    bpy.app.handlers.redo_post.remove(TempLoadCats)
    try:
        bpy.app.handlers.depsgraph_update_pre.remove(InitSavedPanel)
    except:
        pass
    for km in AR_Prop.addon_keymaps:
        bpy.context.window_manager.keyconfigs.addon.keymaps.remove(km)
    AR_Prop.addon_keymaps.clear()