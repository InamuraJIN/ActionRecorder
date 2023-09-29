# Macro Editor
## Macro
![Simple Macro](../images/Simple_Macro.svg)

This is a Macro it can be `activated` and `deactivated` through the check-box and won't be executed if `deactivated`.\
By double-click on the label the Macro can be edited through a dialog.

## Editing Macros

## Operations
![Alt text](../images/MacroEditorOperators.svg)

### Add 

Adds the latest used command as a Macro.
If the setting `Create Empty on Error` is checked it will create an empty Macro if no command is available. (Shortcut: `alt + ,`)
On the first run a popup with Question to enable [Multiline Support](../panels/macro.md#multiline-support) will appear.

### Add Event

This will show a list of possible events that can be used to create more suitable actions.

#### Event List
:::{table}
:widths: auto
| Event           | Description                                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Clipboard       | Adds a new Macro with content of the Clipboard to the selected Action                                                                      |
| Timer           | Wait the specified time and then continue playing the Action                                                                               |
| Render Complete | Execute the blow Macros after a render completed rendering <br> **Note**: No alters will be shown                                          |
| Loop            | Loop the below Macros the given amount of time. <br> **Note**: EndLoop is need to mark the end of the loop otherwise this event is skipped |
| EndLoop         | Marks the end of the loop block                                                                                                            |
| Select Object   | Gives the option to select a specific Object in the Scene                                                                                  |
| Run Script      | Select a text from the Texteditor that is saved internally and will be executed                                                            |
:::

### Remove

Remove the selected Macro

### Move Up

Moves the selected Macro one position up

### Move Down

Moves the selected Macro one position down

## Multiline Support

:::{figure-md}
![Multiline Support Install](../images/MacroEditor_MultilineInstall.png)

First Popup to install Multiline Support
:::

If `Don't Ask Again` is checked it can be later installed in the Preferences

:::{figure-md}
![Multiline Preferences](../images/Preferences_SettingsMultiline.png)

Later install in the Preferences
:::

If Install is pressed the Popup will change to the following:
![Multiline Installing](../images/MacroEditor_MultilineInstalling.png)

After the installation finished the following appear:
![Multiline Installed](../images/MacroEditor_MultilineInstalled.pngstergrafik.png)