# Templates

Templates are an alternative way to integrate users custom menus into your skin. They allow you to provide a one or more templates containing any Kodi GUI controls you like, and insert information from the menu items into them.

They have a number of advantages over the traditional Skin Shortcuts implementation. For example, all sub menu's can be in their own lists and so can have visible/hidden animation. Similarly widgets can be bult individually, allowing them to be switched between without the contents having to be reloaded.

## templates.xml

To use templates, you need to inlclude a template.xml file in your skins shortcuts directory, with all content within a `<template />` element.

If this file is present Skin Shortcuts will automatically build your templates alonside its traditional includes.

```
<?xml version="1.0" encoding="UTF-8"?>
<template>
	<!-- All elements here -->
</template>
```

## Types of templates

Skin Shortcuts supports three types of template - one for sub menu's; one for any other content based off the properties of the main menu items in the users custom menus; one for content based off the properties of a sub menu item in the users custom menus.

#### Sub menu template

```
<submenu include="[include]" level="[level]" name="[name]">
	<property />
	<controls>
		<your>
			<kodi>
				<controls and="tags">
					<skinshortcuts insert="insert">items</skinshortcuts>
				</controls>
			</kodi>
		</your>
	</controls>
	<items insert="[insert]">
		<property />
		<controls />
	</items>
</submenu>
```

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[include]` | Yes | The name of the include this will be added to, appended to skinshortcuts-templates-. If ommitted, it will be added to skinshortcuts-template |
| `[level]` | Yes | If building multiple sub-menu levels, specifies which level this applies to. Omit for the default level (0). |
| `[name]` | Yes | For use with additional groups, the name of the group |
| `<property />` | Yes | [Read More](#property-elements). Note that properties in the main template will be generated from the main menu item. Properties in the sub-template (`<items />`) will be generated from the submenu item |
| `<skinshortcuts>items</skinshortcuts>` | | This will be replaced with the items the user has chosen for the main menu |
| `[insert]` | Yes | Rather than including all menu items directly, you can build your own list from a sub-template. In this case, the `[insert]` is the id of the sub-template whose content will be inserted. See below for more details |
| `<skinshortcuts>visibility</skinshortcuts>` | | This will be replaced with a visibility condition based on the focus of the main menu |
| `<item />` | Yes | Defines a sub-template to be inserted into the main template. See below for more details |

For each sub-menu that is built, a separate set of controls will be generated based on the template. You can include multiple templates with different level/name attributes.

If the level or name attributes are specified, the script will match the first template found with the same attributes, or fall back to the first template without these attributes.

The `<controls />` element must be included. Put your gui xml within.

##### Sub-Template

It's possible to include one or more additional templates within your submenu template, the results of which are inserted into the submenu template itself.

The submenu template itself builds once for each submenu you have. The sub-templates will build once for each menu item within that submenu, allowing you to customise what information from the submenu items you wish to use within the template.

They are defined within a submenu template with an `<items insert="[insert]" />` element, where `[insert]` is the ID that you identify the sub-template from.

They inherit all properties defined by the primary submenu template - all of which are based on the main menu item associated with the submenu. You can then define additional properties, which will be based on the individual submenu item that the template is being built for.

They are inserted into the submenu template by including `<skinshortcuts insert="[insert]">items</skinshortcuts>`, where `[insert]` is the id you have assigned to the sub-template.

#### Other template

```
<other include="[include]">
	<condition />
	<match />
	<property />
	<controls>
		<your>
			<kodi>
				<controls and="tags">
					<skinshortcuts>visibility</skinshortcuts>
					<custom tag="$SKINSHORTCUTS[propertyName]">$SKINSHORTCUTS[propertyName]</custom>
				</controls
			</kodi>
		</your>
	</controls>
	<variables>
		<variable name="customvariable">
			<value condition="SKINSHORTCUTS[propertyName]">$SKINSHORTCUTS[propertyName]</value>
		</variable>
	</variables>
</other>
```

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[include]` | Yes | The name of the include this will be added to, appended to skinshortcuts-templates-. If ommitted, it will be added to skinshortcuts-template |
| `<condition />` | Yes | [Read More](#condition-elements) |
| `<match />` | Yes | [Read More](#match-elements) |
| `<property />` | Yes | [Read More](#property-elements) |
| `<skinshortcuts>visibility</skinshortcuts>` | Yes | This will be replaced with a visibility condition based on the focus of the main menu |
| `$SKINSHORTCUTS[propertyName]` | Yes | This will be replaced by the value of a matched <property /> element |

The `<controls />` element is where you put your Kodi GUI xml that should be built by the template.

The `<variables />` element is where you define any variables that should be built by the template. At least one of them must be included. You must include the `<variable>` element, with as many `<value>` sub-elements as needed.

One Other template will be built for each main menu item per [include]. Use different [include]'s to build multiple Other templates.

#### Submenu-other template

Submenu-other templates act just as a regular other template except that they build based on the properties of a submenu item, and they are defined differently.

```
<submenuOther include="[include]" container="[container]" level="[level]" />
```

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[container]` | Yes | The ID of the container holding the submenu. This is used to build visibilty conditions and, if ommited, these won't be available. |
| `[level]` | Yes | If building multiple sub-menu levels, specifies which level this applies to. Omit for the default level (0). |

For usage, see 'Other' templates documentation, above.

## Condition elements

Condition elements are used to decide whether an Other template should be built, dependant on the items in the main menu. You may use multiple Condition elements - unless you specify a `<match />` element, the template will only be built if they all match.

`<condition tag="[tag]" attribute="[attributeName]|[attributeValue]">[textValue]</condition>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[tag]` | | The main menu must have an element with this tag |
| `[attributeName]|[attributeValue]` | Yes | The element must have an attribute with the name `[attributeName]` and the value `[attributeValue]` |
| `[textValue]` | Yes | The element must have this value |

For example, to match against the following element in a main menu item:

`<property name="widgetType">myWidgetGrouping</property>`

The `<condition />` would be

`<condition tag="property" attribute="name|widgetType">myWidgetGrouping</condition>`

## Match elements

If you are using multiple condition elements, you can include a match element to speicify whether any or all of the conditions must be met for the template to be built

`<match>[any/all]</match>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| [any/all] | | set as 'any' for the template to be built if any of the conditions match|
| | | set as 'all' for the temlate to be built if all of the conditions match (default behaviour) |

e.g.

`<match>any</match>`

## Property elements

Property elements allow you to directly write values into your Other template based on the values of the main menu item the template is being built against. You may include multiple `<property />` elements - the first one matched will be used.

#### Set a property to the value of the main menu item

You can directly pull out any of the properties of the main menu item into a property element.

<property name="[propertyName]" tag="[tag]" attribute="[attributeName|attributeValue" />

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[name]` | | The name of the property you are setting |
| `[tag]` | | The main menu must have an element with this tag |
| `[attributeName]|[attributeValue]` | | The element must have an attribute with the name `[attributeName]` and the value `[attributeValue]` |

For example, to put the following main menu property into a `$SKINSHORTCUTS[widgetPath]` property:

`<property name="widgetPath">[widgetPath]</property>`

The `<property />` would be

`<property name="widgetPath" tag="property" attribute="name|widgetPath" />`

#### Set a property based on the value of a main menu item

You can set a property to a custom value, dependant on what the value of a property in the main menu item is. For example, you could set an artwork property to the image you want to display, based on the widgetType property of the main menu item.

`<property name="[propertyName]" tag="[tag]" attribute="[attributeName]|[attributeValue]" value="[textValue]">[propertyValue]</property>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[name]` | | The name of the property you are setting |
| `[tag]` | Yes | The main menu must have an element with this tag
| `[attributeName]|[attributeValue]` | Yes | The element must have an attribute with the name `[attributeName]` and the value `[attributeValue]` |
| `[textValue]` | Yes | The elment must have this value - you may match against multiple values by splitting them with a pipe - `|` - symbol |
| `[propertyValue]` | Yes | What you are setting the property to. |

For example, to set `$SKINSHORTCUTS[artwork]` to `ListItem.Art(tvshow.poster)` for the following main menu property:-

`<property name="widgetType">tvshows</property>`

The `<property />` would be

`<property name="artwork" tag="property" attribute="name|widgetType" value="tvshows">ListItem.Art(tvshow.poster)</property>`

#### Set a property based on multiple elements

You can set a property to a single value based on different matching elements within the menu item. For example:

```
<property name="leftartwork" propertyValue="5">
	<rule tag="property" attribute="name|widgetStyle" value="Panel" />
	<rule tag="property" attribute="name|widgetArt" value="Poster" />
	<rule tag="property" attribute="name|widgetCase" value="Glass" />
</property>
```

Would set the property `$SKINSHORTCUTS[leftartwork]`to the value of `5` if any of the three rules match.

By default, this property will match if any of the rules match. To only match the property if all of the rules match, include `<match>all</match>` as a sub element.

Note, when setting a property based on multiple elements, you /must/ specify the propertyValue you want assigned - you cannot assign the property to the value of the menu items element that you are checking against.

#### Fallback value

If none of the `<property />` elements match, the property will be an empty string. You can set an alternative fallback value by including the following as the final element in a list of `<property />`'s

`<property name="[propertyName]">[propertyValue]</property>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[name]` | | The name of the property you are setting |
| `[propertyValue]` | | What you are setting the property to |

#### Set the Property to an Include

If you wish to use a Kodi `<include />` as the value of a `$SKINSHORTCUTS[]` property, set the value to `$INCLUDE[includename]`. When the template is written, this will be replaced with an `<include />` element.

#### Set the Property to the ID of the main menu item

You can retrieve the id of the main menu item and place it into a property:-

`<property name="[propertyName]" tag="mainmenuid" />`

#### Using a Property element in your template

Once the property has been set, you can use `$SKINSHORTCUTS[propertyName]` in either an attribute or the value of any Kodi GUI element. It will be replaced with the value of the property.

## Property Groups

You may find that you have multiple `<property />` elements common to multiple templates. In this case you may consider moving some to a property group.

```
<propertyGroup name="myPropertyGroup">
	<property ... />
	<property ... />
	<property ... />
	...
</propertyGroup>
```

The property group can then be included in a template with:

`<propertyGroup>myPropertyGroup</propertyGroup>`

Note that property groups are processed after any properties defined in the template directly.

## Get value from Python

It is possible to run very simple Python scripts within the template to evaluate conditions and have the returned value used in your template. All properties that you have pulled out from a menu item are available via their name. For example, if you have pulled out the mainmenuid into a property named 'id':

`<property name="id" tag="mainmenuid" />`

You could adjust the position of an item as follows:

`<top>$PYTHON[100 + (50 * int(id))]</top>`

Another example, it can be useful to know if a widgetPath has a '?' character in it, as appending anything extra to the path would then need prepending with an '&'. A simple Python script - with reference to the note below on the 'in' operator - can return the correct value for you:

`$PYTHON['&amp;' if widgetPath in '?' else '?']`

#### Notes

* All expressions must be valid Python
* Only basic operators are available. Whilst consideration will be given to requests to enable additional operators, this limitation is for security reasons.
* Whilst 'in' is available, for technical reasons its operation is reversed, so if you want to know if `x` is in `y`, you'd use `if y in x`.
* All properties are passed into your Python script as strings. To use them in mathematical expressions, they must be converted to integers.

## Moving properties to an include using `$PARAM` (KODI 15+)

You can move any `$SKINSHORTCUTS[propertyName]` to an include inside your skin's xml files using `$PARAM[paramName]`.
For more informations about params : [Use params in includes](http://kodi.wiki/view/Skinning_Manual#Use_params_in_includes).

When using `$PARAM[paramName]` in your skin's xml, it will be automatically replaced by the corresponding `$SKINSHORTCUTS[propertyName]` you set.

```
<other include="[include]">
	<property attribute=="[attributeName]|[attributeValue]" tag="[tag]" name="[propertyName]"/>
	<controls>
		<control type="group">
			<skinshortcuts>visibility</skinshortcuts>
			<include name="[myskinInclude]">
				<param name="[paramName]" value="$SKINSHORTCUTS[propertyName]" />
			</include>
		</control>
	</controls>
</other>
```

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[attributeName]|[attributeValue]` | Yes | The element must have an attribute with the name `[attributeName]` and the value `[attributeValue]` |
| `[tag]` | | The main menu must have an element with this tag |
| `[propertyName]` | | The main menu must have an element with this tag |
| `[myskinInclude]` | | The given name of your include inside skin's xml files |
| `[paramName]` | | The given name of your param inside skin's xml files |
| `$SKINSHORTCUTS[propertyName]` | | This will be replaced by the value of a matched <property /> element |

For example, to move a dynamic id, content and target, you can use the following code as template :

```
<other include="MyHomeInclude">
    <property attribute="name|widgetPath" tag="property" name="path"/>
    <property attribute="name|widgetTarget" tag="property" name="target"/>
    <property name="target"/>
    <property name="id" tag="mainmenuid" />
	<controls>
		<control type="group">
			<skinshortcuts>visibility</skinshortcuts>
			<include name="MyIncludesInclude">
				<param name="Id" value="80$SKINSHORTCUTS[id]" />
                <param name="Target" value="$SKINSHORTCUTS[target]" />
                <param name="Path" value="$SKINSHORTCUTS[path]" />
			</include>
		</control>
	</controls>
</other>
```

NOTE - `$PARAM[Id]` has here the value `80$SKINSHORTCUTS[id]` : This will return for item n° 10 the value `8010`. It's useful when using the same container for multiple contents since an include doesn't refresh.
You can then use the properties moved to params inside an includes file (includes.xml or wathever name you used) like :

```
<include name="MyincludesInclude">
	<control type="panel" id="$PARAM[Id]">
		...
		<itemlayout>
		...
		</itemlayout>
		<focusedlayout>
		...
		</focusedlayout>
		<content target="$PARAM[Target]">$PARAM[Path]</content>
	</control>
</include>
```

## A simple example

This example builds the sub menu in a template, so the sub menu for each main menu item is in its own list with visible/hidden animation.

It also builds a widget template in a separate include, with the content set via properties.

As no include attribute is provided for the sub menu template, it is included in the skin with:-

`<include>skinshortcuts-template</include>`

The Other template for the widgets specifies an include attribute of "widget", and so are included with

`<include>skinshortcuts-template-widget</include>`

```
<template>
	<submenu>
		<controls>
			<!-- Submenu -->
			<control type="fixedlist" id="9001">
				<!-- Include the visibility condition -->
				<skinshortcuts>visibility</skinshortcuts>
				<include>submenuList</include>
				<include>submenuAnimation</include>
				<itemlayout width="216" height="25">
					<include>menuLayout</include>
				</itemlayout>
				<focusedlayout width="216" height="25">
					<include>menuFocusedLayout</include>
				</focusedlayout>
				<content>
					<!-- Include the items within the submenu -->
					<skinshortcuts>items</skinshortcuts>
				</content>
			</control>
		</controls>
	</submenu>
	
	<other include="widget">
		<!-- We're going to use this template for all widgets with a widgetPath element -->
		<condition tag="property" attribute="name|widgetPath" />

		<!-- Retrieve the widgetPath and widgetTarget properties -->
		<property name="content" tag="property" attribute="name|widgetPath" />
		<property name="target" tag="property" attribute="name|widgetTarget" />

		<!-- For TV Shows, we want to specify the artwork as the tv show poster, otherwise we'll use the icon -->
		<property name="artwork" tag="property" attribute="name|widgetType" value="tvshows">$INFO[ListItem.Art(tvshow.poster)]</property>
		<property name="artwork">$INFO[ListItem.Icon]</property>

		<controls>
			<control type="list" id="9002">
				<skinshortcuts>visibility</skinshortcuts>
				<include>mediaList</include>
				<layout>
					<include name="mediaLayout">
						<param name="artwork" value="$SKINSHORTCUTS[artwork]"/>
					</include>
				</layout>
				<focusedlayout>
					<include name="mediaFocusedLayout">
						<param name="artwork" value="$SKINSHORTCUTS[artwork]"/>
					</include>
				</focusedlayout>
				<content target="$SKINSHORTCUTS[target]">$SKINSHORTCUTS[content]</content>
			</control>
		</controls>
	</other>
</template>
```

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)
