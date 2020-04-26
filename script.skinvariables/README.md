# script.skinvariables
A helper script for Kodi skinners to construct multiple variables

## Variable Builder

SkinVariables provides a tool for skinners to create a variable template which generates variables for multiple containers and/or list items.

To use this feature, create a plain text file in the skin's shortcuts directory  
```
kodi/addons/SKINNAME/shortcuts/skinvariables.json
```

## The Template
In the skinvariables.json you create a template like so
```json
[
    {
        "name"          : "Image_Poster",
        "containers"    : [51,52],
        "listitems"     : {"start": 1, "end": 2},
        "values"        : [
                            {"!String.IsEmpty({listitem}.Art(tvshow.poster))": "$INFO[{listitem}.Art(tvshow.poster)]"},
                            {"!String.IsEmpty({listitem}.Art(poster))": "$INFO[{listitem}.Art(poster)]"}
                          ]
    },
    {
        "name"          : "Image_Landscape",
        "containers"    : [51,52],
        "listitems"     : {"start": 1, "end": 2},
        "values"        : [
                            {"!String.IsEmpty({listitem}.Art(landscape))": "$INFO[{listitem}.Art(landscape)]"},
                            {"!String.IsEmpty({listitem}.Art(fanart))": "$INFO[{listitem}.Art(fanart)]"}

                          ]
    }
]
```

| Key | Purpose |
| :--- | :--- |
| "name" | \[required\] The name of the variable to build. One variable will be built for each specified container and each listitem position in the range specified. Variables follow the naming pattern `{name}_C{containerID}_{listitemposition}` |
| "containers" | \[optional\] Each of the container IDs that you wish to build a variable for. A variable will also be built without a specified container |
| "listitems" | \[optional\] Builds a variable for each listitem position in the range. A variable will also be built for a listitem without a specified position. |
| "values" | \[required\] The rules of the variable. In each pair, the left side is the `<value condition="CONDITION">` and the right side is the resulting value. |
| {listitem} | Replaced by the specific container and listitem - e.g. in Image_Landscape_C51_5 it will be `Container(51).ListItem(5).` |
| {listitemabsolute} | Like {listitem} but the absolute position - e.g. `Container(51).ListItemAbsolute(5).` |
| {listitemnowrap} | Like {listitem} but the nowrap position - e.g. `Container(51).ListItemNoWrap(5).` |
| {listitemposition} | Like {listitem} but the onscreen position - e.g. `Container(51).ListItemPosition(5).` |



## Building the Variables

To build the variables from the template
```
runscript(script.skinvariables)
```

The script will only build the variables if the template has changed.  
You can force a rebuild by adding the force argument `runscript(script.skinvariables,force)`

This command will generate a file in the skin's xml folder called `script-skinvariables-includes.xml`  
You can specify the folder with the folder argument `runscript(script.skinvariables,folder=1080i)`

You need to add this file to your `Includes.xml`  
```
<include file="script-skinvariables-includes.xml" />
```

A variable for each position in the listitem range and for each container specified will be outputted to that includes file. Additionally, a base variable without any container or position will be built.

For instance, the above will build:
```xml
<variable name="Image_Poster">
    <value condition="!String.IsEmpty(ListItem.Art(tvshow.poster))">$INFO[ListItem.Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(ListItem.Art(poster))">$INFO[ListItem.Art(poster)]</value>
</variable>
<variable name="Image_Poster_C51">
    <value condition="!String.IsEmpty(Container(51).ListItem.Art(tvshow.poster))">$INFO[Container(51).ListItem.Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(Container(51).ListItem.Art(poster))">$INFO[Container(51).ListItem.Art(poster)]</value>
</variable>
<variable name="Image_Poster_C51_1">
    <value condition="!String.IsEmpty(Container(51).ListItem(1).Art(tvshow.poster))">$INFO[Container(51).ListItem(1).Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(Container(51).ListItem(1).Art(poster))">$INFO[Container(51).ListItem(1).Art(poster)]</value>
</variable>
<variable name="Image_Poster_C51_2">
    <value condition="!String.IsEmpty(Container(51).ListItem(2).Art(tvshow.poster))">$INFO[Container(51).ListItem(2).Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(Container(51).ListItem(2).Art(poster))">$INFO[Container(51).ListItem(2).Art(poster)]</value>
</variable>
<variable name="Image_Poster_C52">
    <value condition="!String.IsEmpty(Container(52).ListItem.Art(tvshow.poster))">$INFO[Container(52).ListItem.Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(Container(52).ListItem.Art(poster))">$INFO[Container(52).ListItem.Art(poster)]</value>
</variable>
<variable name="Image_Poster_C52_1">
    <value condition="!String.IsEmpty(Container(52).ListItem(1).Art(tvshow.poster))">$INFO[Container(52).ListItem(1).Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(Container(52).ListItem(1).Art(poster))">$INFO[Container(52).ListItem(1).Art(poster)]</value>
</variable>
<variable name="Image_Poster_C52_2">
    <value condition="!String.IsEmpty(Container(52).ListItem(2).Art(tvshow.poster))">$INFO[Container(52).ListItem(2).Art(tvshow.poster)]</value>
    <value condition="!String.IsEmpty(Container(52).ListItem(2).Art(poster))">$INFO[Container(52).ListItem(2).Art(poster)]</value>
</variable>
<variable name="Image_Landscape">
    <value condition="!String.IsEmpty(ListItem.Art(landscape))">$INFO[ListItem.Art(landscape)]</value>
    <value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value>
</variable>
<variable name="Image_Landscape_C51">
    <value condition="!String.IsEmpty(Container(51).ListItem.Art(landscape))">$INFO[Container(51).ListItem.Art(landscape)]</value>
    <value condition="!String.IsEmpty(Container(51).ListItem.Art(fanart))">$INFO[Container(51).ListItem.Art(fanart)]</value>
</variable>
<variable name="Image_Landscape_C51_1">
    <value condition="!String.IsEmpty(Container(51).ListItem(1).Art(landscape))">$INFO[Container(51).ListItem(1).Art(landscape)]</value>
    <value condition="!String.IsEmpty(Container(51).ListItem(1).Art(fanart))">$INFO[Container(51).ListItem(1).Art(fanart)]</value>
</variable>
<variable name="Image_Landscape_C51_2">
    <value condition="!String.IsEmpty(Container(51).ListItem(2).Art(landscape))">$INFO[Container(51).ListItem(2).Art(landscape)]</value>
    <value condition="!String.IsEmpty(Container(51).ListItem(2).Art(fanart))">$INFO[Container(51).ListItem(2).Art(fanart)]</value>
</variable>
<variable name="Image_Landscape_C52">
    <value condition="!String.IsEmpty(Container(52).ListItem.Art(landscape))">$INFO[Container(52).ListItem.Art(landscape)]</value>
    <value condition="!String.IsEmpty(Container(52).ListItem.Art(fanart))">$INFO[Container(52).ListItem.Art(fanart)]</value>
</variable>
<variable name="Image_Landscape_C52_1">
    <value condition="!String.IsEmpty(Container(52).ListItem(1).Art(landscape))">$INFO[Container(52).ListItem(1).Art(landscape)]</value>
    <value condition="!String.IsEmpty(Container(52).ListItem(1).Art(fanart))">$INFO[Container(52).ListItem(1).Art(fanart)]</value>
</variable>
<variable name="Image_Landscape_C52_2">
    <value condition="!String.IsEmpty(Container(52).ListItem(2).Art(landscape))">$INFO[Container(52).ListItem(2).Art(landscape)]</value>
    <value condition="!String.IsEmpty(Container(52).ListItem(2).Art(fanart))">$INFO[Container(52).ListItem(2).Art(fanart)]</value>
</variable>
```
