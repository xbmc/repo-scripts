# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import ast
import operator
import os
import xml.etree.ElementTree as ETree

import xbmc
import xbmcvfs
from simpleeval import SimpleEval
from simpleeval import simple_eval

from .common import log
from .constants import SKIN_SHORTCUTS_PATH


class Template:
    def __init__(self):
        # Load the skins template.xml file
        self.templatepath = os.path.join(SKIN_SHORTCUTS_PATH, "template.xml")
        self.other_templates = []

        try:
            self.tree = ETree.parse(self.templatepath)

            log("Loaded template.xml file")

            # Pull out the names and includes of the 'other' templates -
            # used to generate accurate progress and to build empty
            # 'other' templates if necessary
            for other_template in self.tree.getroot().findall("other"):
                include_name = "skinshortcuts-template"
                if "include" in other_template.attrib:
                    include_name = "skinshortcuts-template-%s" % \
                                   (other_template.attrib.get("include"))

                if include_name not in self.other_templates:
                    self.other_templates.append(include_name)

        except:
            # We couldn't load the template.xml file
            if xbmcvfs.exists(self.templatepath):
                # Unable to parse template.xml
                log("Unable to parse template.xml. Invalid xml?")
            else:
                # No template.xml
                self.tree = None

        # Empty variable which will contain our base elementree (passed from buildxml)
        self.includes = None

        # Empty progress which will contain the Kodi progress dialog gui (passed from buildxml)
        self.progress = None
        self.percent = None
        self.current = None

        # List which will contain 'other' elements we will need to finalize (we won't have all the
        # visibility conditions until the end)
        self.finalize = []

        # Initialize simple eval
        self.simple_eval = SimpleEval()
        self.simple_eval.operators[ast.In] = operator.contains

        self.hashable = set()
        self.hashable.add(self.templatepath)

    def parse_items(self, menu_type, level, items, profile, profile_visibility,
                    visibility_condition, menu_name,
                    mainmenu_id=None, build_others=False, mainmenuitems=None):
        # This will build an item in our includes for a menu
        if self.includes is None or self.tree is None:
            return

        # Get the template for this menu
        if menu_type == "mainmenu":
            template = self.tree.find("mainmenu")
            if template is not None:
                template = self.copy_tree(template)

        else:
            if len(items.findall("item")) == 0:
                return

            template = self.find_submenu(menu_name, level)

        if template is not None:
            # Found a template - let's build it
            if menu_type == "mainmenu":
                log("Main menu template found")
            else:
                log("Submenu template found")

            # We need to check that the relevant includes existing
            # First, the overarching include
            include_name = "skinshortcuts-template"
            if "include" in template.attrib:
                include_name += "-%s" % template.attrib.get("include")

            _ = self.get_include(self.includes, include_name, profile_visibility, profile)
            include_tree = self.get_include(self.includes, "%s-%s" % (include_name, profile),
                                            None, None)

            # If we've been passed any mainmenu items, retrieve their properties
            properties = {}
            if mainmenuitems is not None:
                properties = self.get_properties(template, mainmenuitems)

            # Now replace all <skinshortcuts> elements with correct data
            self.replace_elements(template.find("controls"), visibility_condition,
                                  profile_visibility, items, properties,
                                  customitems=template.findall("items"))

            # Add the template to the includes
            for child in template.find("controls"):
                include_tree.append(child)

        # Now we want to see if any of the main menu items match a template
        if not build_others or len(self.other_templates) == 0:
            return

        # If we've been passed any mainmenu items, retrieve the id of the main menu item
        root_id = None
        if mainmenuitems is not None:
            root_id = mainmenuitems.attrib.get("id")

        progress_count = 0
        num_templates = 0

        if menu_type == "mainmenu":
            log("Building templates")
        else:
            # Switch menutype for level for submenu templates, to make it easier to pass in
            menu_type = level

        for item in items:
            progress_count = progress_count + 1
            if menu_type == "mainmenu":
                # First we need to build the visibilityCondition, based on the items
                # submenuVisibility element, and the mainmenuID
                visibility_name = ""
                for element in item.findall("property"):
                    if "name" in element.attrib and \
                            element.attrib.get("name") == "submenuVisibility":
                        visibility_name = element.text
                        break

                final_visibility = \
                    "String.IsEqual(Container(%s).ListItem.Property(submenuVisibility),%s)" % \
                    (mainmenu_id, visibility_name)

            else:
                # First we need to build the visibilityCondition, based on the visibility condition
                #  passed in, and the submenuVisibility element
                visibility_name = ""
                for element in item.findall("property"):
                    if "name" in element.attrib and element.attrib.get("name") == "labelID":
                        visibility_name = element.text
                        break

                # Handle auto visibility condition if the labelID is a number that translates to
                # a localised string
                if visibility_name.isdigit() and \
                        xbmc.getLocalizedString(int(visibility_name)) != "":
                    visibility_name = "$LOCALIZE[%s]" % visibility_name

                final_visibility = "[%s + String.IsEqual(Container(::SUBMENUCONTAINER::)" \
                                   ".ListItem.Property(labelID),%s)]" % \
                                   (visibility_condition, visibility_name)

            # Now find a matching template - if one matches, it will be saved to be processed
            # at the end (when we have all visibility conditions)
            num_templates += self.find_other(item, profile, profile_visibility,
                                             visibility_condition, final_visibility,
                                             menu_type, root_id)
            if menu_type == "mainmenu":
                self.progress.update(
                    int(self.current + ((float(self.percent) / float(len(items))) * progress_count))
                )

        if num_templates != 0:
            log("%d templates" % num_templates)

    def write_others(self):
        # This will write any 'other' elements we have into the includes file
        # (now we have all the visibility conditions for them)
        if self.includes is None or self.tree is None:
            return

        if len(self.finalize) == 0:
            return

        final_variables = {}
        final_variable_names = []

        for template in self.finalize:
            # Get the group name
            name = "skinshortcuts-template"
            if "include" in template.attrib:
                include_name = template.attrib.get("include")
                name += "-%s" % include_name

                # Remove the include from our list of other templates,
                # as we don't need to build an empty one
                if name in self.other_templates:
                    self.other_templates.remove(name)

            # Loop through any profiles we have
            for profile in template.findall("skinshortcuts-profile"):
                visibility_condition = None
                # Build the visibility condition
                for condition in profile.findall("visible"):
                    if visibility_condition is None:
                        visibility_condition = condition.text

                    elif condition.text != "":
                        visibility_condition += " | %s" % condition.text

                # Get the include this will be done under
                _ = self.get_include(self.includes, name, profile.attrib.get("visible"),
                                     profile.attrib.get("profile"))
                include = self.get_include(self.includes, "%s-%s" %
                                           (name, profile.attrib.get("profile")),
                                           None, None)  # profile.attrib.get( "visible" ) )

                # Create a copy of the node with any changes within (this time it'll be visibility)
                final = self.copy_tree(template)
                self.replace_elements(final, visibility_condition,
                                      profile.attrib.get("visible"), [])

                # Add the template to the includes
                controls = final.find("controls")
                if controls is not None:
                    for child in controls:
                        include.append(child)

                # Process the variables
                variables = final.find("variables")
                if variables is not None:
                    for variable in variables.findall("variable"):
                        # If the profile doesn't have a dict in final_variables, create one
                        profile_visibility = profile.attrib.get("visible")
                        if profile_visibility not in final_variables:
                            final_variables[profile_visibility] = {}

                        # Save the variable name
                        var_name = variable.attrib.get("name")
                        if var_name not in final_variable_names:
                            final_variable_names.append(var_name)

                        # Get any existing values for this profile + variable
                        new_variables = []
                        if var_name in final_variables[profile_visibility]:
                            new_variables = final_variables[profile_visibility][var_name]

                        # Loop through new values provided by this template
                        for value in variable.findall("value"):
                            condition = ""
                            if "condition" in value.attrib:
                                condition = value.attrib.get("condition")

                            # Add the new condition/value pair only if it really is new
                            new_value = (condition, value.text)
                            if new_value not in new_variables:
                                new_variables.append(new_value)

                        # Add the values into the dict
                        final_variables[profile_visibility][var_name] = new_variables

        # And now write the variables
        for variable_name in final_variable_names:
            element = ETree.SubElement(self.includes, "variable")
            element.set("name", variable_name)
            for condition, value in self.parse_variables(variable_name, final_variables):
                value_element = ETree.SubElement(element, "value")
                value_element.text = value
                if condition != "":
                    value_element.set("condition", condition)

        # If there are any 'other' templates that we haven't built, build an empty one
        for other_template in self.other_templates:
            # Get the include this will be built in
            root = self.get_include(self.includes, other_template, None, None)
            ETree.SubElement(root, "description").text = \
                "This include was built automatically as the template didn't match any menu items"

    @staticmethod
    def parse_variables(variable_name, all_variables):
        # This function will return all condition/value elements for a given variable,
        # including adding profile conditions
        return_variables = []
        no_condition = []

        # Firstly, lets pull out the specific variables from all the variables we've been passed
        limited_variables = {}
        for profile in all_variables:
            if variable_name in all_variables[profile]:
                limited_variables[profile] = all_variables[profile][variable_name]

        num_profiles = len(limited_variables)
        for profile in list(limited_variables.keys()):
            while len(limited_variables[profile]) != 0:
                # Grab the first value from the list
                value = limited_variables[profile].pop(0)
                profiles = [profile]

                # Now check if any other profile has that value
                for additional_profile in list(limited_variables.keys()):
                    if value in limited_variables[additional_profile]:
                        # It does - remove it and add the profile visibility
                        # to the one we already have
                        profiles.append(additional_profile)
                        limited_variables[additional_profile].remove(value)

                # Check if we need to add profile visibility
                if len(profiles) == num_profiles:
                    # We don't
                    if value[0] == "":
                        no_condition.append(value)
                    else:
                        return_variables.append(value)

                else:
                    # We do
                    condition = None
                    for profile_visibility in profiles:
                        if condition is None:
                            condition = profile_visibility
                        else:
                            condition = "%s | %s" % (condition, profile_visibility)

                    if value[0] == "":
                        no_condition.append((condition, value[1]))
                    else:
                        return_variables.append(("%s + [%s]" % (condition, value[0]), value[1]))

        return return_variables + no_condition

    @staticmethod
    def get_include(tree, name, condition, profile):
        # This function gets an existing <include/>, or creates it
        for include in tree.findall("include"):
            if include.attrib.get("name") == name:
                if condition is None:
                    return include

                # We've been passed a condition, check there's an include with that
                # as condition and name as text
                for vis_include in include.findall("include"):
                    if vis_include.attrib.get("condition") == condition:
                        return include

                # We didn't find condition,so create it
                vis_include = ETree.SubElement(include, "include")
                vis_include.set("condition", condition)
                vis_include.text = "%s-%s" % (name, profile)

                return include

        # We didn't find the node, so create it
        new_include = ETree.SubElement(tree, "include")
        new_include.set("name", name)

        # If we've been passed a condition, create an include with that as condition
        # and name as text
        if condition is not None:
            vis_include = ETree.SubElement(new_include, "include")
            vis_include.set("condition", condition)
            vis_include.text = "%s-%s" % (name, profile)

        return new_include

    def find_submenu(self, name, level):
        # Find the correct submenu template
        return_elem = None
        for elem in self.tree.findall("submenu"):
            # Check if the level matched
            if level == 0:
                # No level, so there shouldn't be a level attrib
                if "level" in elem.attrib:
                    continue

            else:
                # There is a level, so make sure there's a level attrib
                if "level" not in elem.attrib:
                    continue

                # Make sure the level values match
                if elem.attrib.get("level") != str(level):
                    continue

            # If there's a name attrib, check if it matches
            if "name" in elem.attrib:
                if elem.attrib.get("name") == name:
                    # This is the one we want :)
                    return self.copy_tree(elem)

                continue

            # Save this, in case we don't find a better match
            return_elem = elem

        if return_elem is None:
            return None

        return self.copy_tree(return_elem)

    def find_other(self, item, profile, profile_visibility, simple_visibility, visibility_condition,
                   menu_type, root_id):
        # Find a template matching the item we have been passed
        found_template_includes = []
        num_templates = 0
        search_type = "other"

        if menu_type != "mainmenu":
            search_type = "submenuOther"

        for elem in self.tree.findall(search_type):
            # Check that we don't already have a template for this include
            include_name = None
            if "include" in elem.attrib:
                include_name = elem.attrib.get("include")

            if include_name in found_template_includes:
                continue

            template = self.copy_tree(elem)
            matched = True

            final_visibility = visibility_condition
            if menu_type != "mainmenu":
                # This isn't the main menu

                # First we check if the level matches
                if "level" in elem.attrib:
                    if menu_type != int(elem.attrib.get("level")):
                        continue

                elif menu_type != 0:
                    continue

                # Next we either extend the visibility condition to also match the submenu
                # (if the template provides the submenu container ID),
                # or drop the visibility condition
                if "container" in elem.attrib:
                    final_visibility = visibility_condition.replace("::SUBMENUCONTAINER::",
                                                                    elem.attrib.get("container"))
                else:
                    final_visibility = simple_visibility

            # Check whether the skinner has set the match type
            # (whether all conditions need to match, or any)
            match_type = "all"
            match_elem = template.find("match")
            if match_elem is not None:
                match_type = match_elem.text.lower()
                if match_type not in ["any", "all"]:
                    log("Invalid <match /> element in template")
                    match_type = "all"

                elif match_type == "any":
                    matched = False

            # Check the conditions
            for condition in template.findall("condition"):
                if match_type == "all":
                    if matched is False:
                        break

                    if self.check_condition(condition, item) is False:
                        matched = False
                        break

                else:
                    if True in (matched, self.check_condition(condition, item)):
                        matched = True
                        break

            # If the conditions didn't match, we're done here
            if matched is False:
                continue

            num_templates += 1

            # All the rules matched, so next we'll get any properties
            properties = self.get_properties(template, item)
            if root_id is not None:
                properties["auto-rootID"] = root_id

            # Next up, we do any replacements - EXCEPT for visibility, which
            # we'll store for later (in case multiple items would have an
            # identical template
            self.replace_elements(template.find("controls"), None, None, [], properties)
            self.replace_elements(template.find("variables"), None, None, [], properties)

            # Now we need to check if we've already got a template identical to this
            found_in_previous = False
            for previous in self.finalize:
                # Check that the previous template uses the same include
                include_name_check = include_name
                if include_name is None:
                    include_name_check = "NONE"

                if previous.find("skinshortcuts-includeName").text != include_name_check:
                    continue

                # Compare templates
                if self.compare_tree(template.find("controls"), previous.find("controls")) and \
                        self.compare_tree(template.find("variables"), previous.find("variables")):
                    # They are the same

                    # Add our details to the previous version, so we can build it
                    # with full visibility details later
                    for profile_match in previous.findall("skinshortcuts-profile"):
                        if profile_match.attrib.get("profile") == profile:
                            # Check if we've already added this visibilityCondition
                            for visible in profile_match.findall("visible"):
                                if visible.text == final_visibility:
                                    # The condition is already there
                                    found_in_previous = True

                            # We didn't find it, so add it
                            if not found_in_previous:
                                ETree.SubElement(profile_match, "visible").text = final_visibility
                                found_in_previous = True

                    if found_in_previous is True:
                        break

                    # We didn't find this profile, so add it
                    new_element = ETree.SubElement(previous, "skinshortcuts-profile")
                    new_element.set("profile", profile)
                    new_element.set("visible", profile_visibility)

                    # And save the visibility condition
                    ETree.SubElement(new_element, "visible").text = final_visibility

                    # And we're done
                    found_template_includes.append(include_name)
                    found_in_previous = True

            if found_in_previous is False:
                # We don't have this template saved, so add our profile details to it
                new_element = ETree.SubElement(template, "skinshortcuts-profile")
                new_element.set("profile", profile)
                new_element.set("visible", profile_visibility)

                # Save the visibility condition
                ETree.SubElement(new_element, "visible").text = final_visibility

                new_element = ETree.SubElement(template, "skinshortcuts-includeName")
                if include_name is None:
                    new_element.text = "NONE"
                else:
                    new_element.text = include_name

                # Add it to our finalize list
                self.finalize.append(template)

                # Add that we've found a template for this include
                found_template_includes.append(include_name)

        return num_templates

    @staticmethod
    def check_condition(condition, items):
        # Check if a particular condition is matched for an 'other' template
        if "tag" not in condition.attrib:
            # Tag attrib is required
            return False

        tag = condition.attrib.get("tag")

        attrib = None
        if "attribute" in condition.attrib:
            attrib = condition.attrib.get("attribute").split("|")

        # Find all elements with matching tag
        for item in items.findall(tag):
            if attrib is not None:
                if attrib[0] not in item.attrib:
                    # Doesn't have the attribute we're looking for
                    continue

                if attrib[1] != item.attrib.get(attrib[0]):
                    # This property doesn't match
                    continue

            if condition.text is not None and item.text != condition.text:
                # This property doesn't match
                continue

            # The rule has been matched :)
            return True

        return False

    def get_properties(self, elem, items):
        # Get any properties specified in an 'other' template
        properties = {}

        # Start by finding all properties defined directly in the template
        search_properties = elem.findall("property")

        # Add any properties defined in a property group
        for property_group in elem.findall("propertyGroup"):
            for search_group in self.tree.findall("propertyGroup"):
                if property_group.text.lower() == search_group.attrib.get("name").lower():
                    search_properties += search_group.findall("property")

        # Loop through all the properties
        for prop in search_properties:
            if "name" not in prop.attrib or prop.attrib.get("name") in properties:
                # Name attrib required, or we've already got a property with this name
                continue

            name = prop.attrib.get("name")

            #  Pull out the tag, attribute and value attribs into an array of tuples
            rules = []
            match_any = True
            property_value = None
            if "propertyValue" in prop.attrib:
                property_value = prop.attrib.get("propertyValue")

            # Check for multiple items to match against this single value
            for single_match in prop.findall("rule"):
                attribute = None
                value = None

                if "tag" not in single_match.attrib:
                    # Tag is required, so we'll pass on this
                    log("Trying to match a property without using a tag element")
                    continue

                tag = single_match.attrib.get("tag")

                if "attribute" in single_match.attrib:
                    attribute = single_match.attrib.get("attribute").split("|")

                if "value" in single_match.attrib:
                    value = single_match.attrib.get("value").split("|")

                rules.append((tag, attribute, value, property_value))

            match_all = prop.find("match")
            if match_all is not None and match_all.text.lower() == "all":
                match_any = False

            # If we haven't grabbed anything to match against yet
            if len(rules) == 0:
                if "tag" in prop.attrib:
                    tag = prop.attrib.get("tag")

                    # Special case for the ID of the main menu item
                    if tag.lower() == "mainmenuid":
                        properties[name] = items.attrib.get("id")
                        continue

                    # Pull out the properties we'll match against
                    attribute = None
                    value = None
                    property_value = None

                    if "attribute" in prop.attrib:
                        attribute = prop.attrib.get("attribute").split("|")

                    if "value" in prop.attrib:
                        value = prop.attrib.get("value").split("|")

                    if prop.text:
                        property_value = prop.text

                    rules.append((tag, attribute, value, property_value))

                else:
                    # No tag property, so this will always match (so let's just use it!)
                    if prop.text:
                        properties[name] = prop.text
                    else:
                        properties[name] = ""

                    continue

            if match_any:
                # Match the property if any of the rules match
                matched_rule = False
                for rule in rules:
                    if matched_rule:
                        break

                    # Let's get looking for any items that match
                    tag = rule[0]
                    attrib = rule[1]
                    value = rule[2]

                    for item in items.findall(tag):
                        if attrib is not None:
                            if attrib[0] not in item.attrib:
                                # Doesn't have the attribute we're looking for
                                continue

                            if attrib[1] != item.attrib.get(attrib[0]):
                                # The attributes value doesn't match
                                continue

                        if not item.text:
                            # The item doesn't have a value to match
                            continue

                        if value is not None and item.text not in value:
                            # The value doesn't match
                            continue

                        # We've matched a property :)
                        if rule[3] is not None:
                            properties[name] = rule[3]
                        else:
                            properties[name] = item.text

                        break

            else:
                # Match the property only if all the rules match
                matched_rule = True
                matched_value = []
                for rule in rules:
                    if not matched_rule:
                        matched_value = []
                        break

                    # Let's get looking for any items that match
                    tag = rule[0]
                    attrib = rule[1]
                    value = rule[2]
                    matched_value = rule

                    for item in items.findall(tag):
                        log(repr(attrib))
                        if attrib is not None:
                            if attrib[0] not in item.attrib:
                                # Doesn't have the attribute we're looking for
                                matched_rule = False
                                continue

                            if attrib[1] != item.attrib.get(attrib[0]):
                                # The attributes value doesn't match,
                                # so we don't want to check the rule against it
                                continue

                        if not item.text:
                            # The item doesn't have a value to match
                            matched_rule = False
                            continue

                        if value is not None and item.text not in value:
                            # The value doesn't match
                            matched_rule = False
                            continue

                if matched_rule:
                    # We've matched a property :)
                    if matched_value[3] is not None:
                        properties[name] = matched_value[3]
                    else:
                        # This method only supports setting the property value directly,
                        # so if it wasn't specified, include a log error
                        log("Invalid template - cannot set property directly to menu item "
                            "elements value when using multiple rules for single property")

        return properties

    def combine_properties(self, elem, items, current_properties):
        # Combines an existing set of properties with additional properties
        new_properties = self.get_properties(elem, items)
        for property_name in list(new_properties.keys()):
            if property_name in list(current_properties.keys()):
                continue

            current_properties[property_name] = new_properties[property_name]

        return current_properties

    def replace_elements(self, tree, visibility_condition, profile_visibility, items,
                         properties=None, customitems=None):
        if properties is None:
            properties = {}

        if tree is None:
            return

        for elem in tree:
            # <tag skinshortcuts="visible" /> -> <tag condition="[condition]" />
            if "skinshortcuts" in elem.attrib:
                # Get index of the element
                index = list(tree).index(elem)

                # Get existing attributes, text and tag
                attribs = []
                item_type = ""
                for single_attrib in elem.attrib:
                    if single_attrib == "skinshortcuts":
                        item_type = elem.attrib.get("skinshortcuts")
                    else:
                        attribs.append((single_attrib, elem.attrib.get(single_attrib)))

                text = elem.text
                tag = elem.tag

                # Don't continue is item_type = visibility, and no visibilityCondition
                if item_type == "visibility" and visibility_condition is None:
                    continue

                # Remove the existing element
                tree.remove(elem)

                # Make replacement element
                new_element = ETree.Element(tag)
                if text is not None:
                    new_element.text = text

                for single_attrib in attribs:
                    new_element.set(single_attrib[0], single_attrib[1])

                # Make replacements
                if item_type == "visibility" and visibility_condition is not None:
                    new_element.set("condition", visibility_condition)

                # Insert it
                tree.insert(index, new_element)

            # <tag>$skinshortcuts[var]</tag> -> <tag>[value]</tag>
            # <tag>$skinshortcuts[var]</tag> ->
            # <tag><include>[includeName]</include></tag> (property = $INCLUDE[includeName])
            if elem.text is not None:
                while "$SKINSHORTCUTS[" in elem.text:
                    # Split the string into its composite parts
                    string_start = elem.text.split("$SKINSHORTCUTS[", 1)
                    string_end = string_start[1].split("]", 1)
                    # string_start[ 0 ] = Any code before the $SKINSHORTCUTS property
                    # string_end[ 0 ] = The name of the $SKINSHORTCUTS property
                    # string_end[ 1 ] = Any code after the $SKINSHORTCUTS property

                    if string_end[0] in properties:
                        if properties[string_end[0]].startswith("$INCLUDE["):
                            # Remove text property
                            elem.text = ""
                            # Add include element
                            include_element = ETree.SubElement(elem, "include")
                            include_element.text = properties[string_end[0]][9:-1]

                        else:
                            elem.text = string_start[0] + properties[string_end[0]] + string_end[1]

                    else:
                        elem.text = string_start[0] + string_end[1]

            # <tag attrib="$skinshortcuts[var]" /> -> <tag attrib="[value]" />
            for attrib in elem.attrib:
                value = elem.attrib.get(attrib)
                while "$SKINSHORTCUTS[" in elem.attrib.get(attrib):
                    # Split the string into its composite parts
                    string_start = elem.attrib.get(attrib).split("$SKINSHORTCUTS[", 1)
                    string_end = string_start[1].split("]", 1)

                    if string_end[0] in properties:
                        elem.set(attrib,
                                 string_start[0] + properties[string_end[0]] + string_end[1])
                    else:
                        elem.set(attrib, string_start[0] + string_end[1])

                if value.startswith("$SKINSHORTCUTS[") and value[15:-1] in properties:
                    new_value = ""
                    if value[15:-1] in properties:
                        new_value = properties[value[15:-1]]
                    elem.set(attrib, new_value)

            # <tag>$PYTHON[var]</tag> -> <tag>[result]</tag>
            if elem.text is not None:
                while "$PYTHON[" in elem.text:
                    # Split the string into its composite parts
                    string_start = elem.text.split("$PYTHON[", 1)
                    string_end = string_start[1].split("]", 1)
                    # string_start[ 0 ] = Any code before the $MATHS property
                    # string_end[ 0 ] = The maths to be performed
                    # string_end[ 1 ] = Any code after the $MATHS property

                    string_end[0] = simple_eval("%s" % (string_end[0]), names=properties)

                    elem.text = string_start[0] + str(string_end[0]) + string_end[1]

            # <tag attrib="$PYTHON[var]" /> -> <tag attrib="[value]" />
            for attrib in elem.attrib:
                _ = elem.attrib.get(attrib)
                while "$PYTHON[" in elem.attrib.get(attrib):
                    # Split the string into its composite parts
                    string_start = elem.attrib.get(attrib).split("$PYTHON[", 1)
                    string_end = string_start[1].split("]", 1)

                    string_end[0] = simple_eval("%s" % (string_end[0]), names=properties)

                    elem.set(attrib, string_start[0] + str(string_end[0]) + string_end[1])

            # <skinshortcuts>visible</skinshortcuts> -> <visible>[condition]</visible>
            # <skinshortcuts>items</skinshortcuts> -> <item/><item/>...
            if elem.tag == "skinshortcuts":
                # Get index of the element
                index = list(tree).index(elem)

                # Get the item_type of replacement
                item_type = elem.text

                # Don't continue is item_type = visibility, and no visibilityCondition
                if item_type == "visibility" and visibility_condition is None:
                    continue

                # Remove the existing element
                tree.remove(elem)

                # Make replacements
                if item_type == "visibility" and visibility_condition is not None:
                    # Create a new visible element
                    newelement = ETree.Element("visible")
                    newelement.text = visibility_condition
                    # Insert it
                    tree.insert(index, newelement)

                elif item_type == "items" and customitems is not None and \
                        elem.attrib.get("insert"):
                    for element in self.build_submenu_custom_items(customitems,
                                                                   items.findall("item"),
                                                                   elem.attrib.get("insert"),
                                                                   properties):
                        for child in element:
                            tree.insert(index, child)

                elif item_type == "items":
                    # Firstly, go through and create an array of all items in reverse order, without
                    # their existing visible element, if it matches our visibilityCondition
                    newelements = []
                    if not items:
                        break

                    for item in items.findall("item"):
                        newitem = self.copy_tree(item)

                        # Remove the existing visible elem from this
                        for visibility in newitem.findall("visible"):
                            if visibility.text != profile_visibility:
                                continue
                            newitem.remove(visibility)

                        # Add a copy to the array
                        newelements.insert(0, newitem)

                    if len(newelements) != 0:
                        for element in newelements:
                            # Insert them into the template
                            tree.insert(index, element)

            else:
                # Iterate through tree
                self.replace_elements(elem, visibility_condition, profile_visibility, items,
                                      properties, customitems=customitems)

    def build_submenu_custom_items(self, template, items, insert, current_properties):
        # Builds an 'items' template within a submenu template

        # Find the template with the correct insert attribute
        item_template = None
        for test_template in template:
            if test_template.attrib.get("insert") == insert:
                item_template = test_template
                break

        if item_template is None:
            # Couldn't find a template
            return []

        newelements = []
        for item in items:
            new_element = self.copy_tree(item_template.find("controls"))
            self.replace_elements(
                new_element, None, None, [],
                self.combine_properties(item_template, item, current_properties.copy())
            )
            newelements.insert(0, new_element)

        return newelements

    def copy_tree(self, elem):
        if elem is None:
            return None

        ret = ETree.Element(elem.tag, elem.attrib)
        ret.text = elem.text
        ret.tail = elem.tail

        for child in elem:
            ret.append(self.copy_tree(child))

        return ret

    def compare_tree(self, element_1, element_2):
        if element_1 is None and element_2 is None:
            return True

        if element_1 is None or element_2 is None:
            return False

        if element_1.tag != element_2.tag:
            return False

        if element_1.text != element_2.text:
            return False

        if element_1.tail != element_2.tail:
            return False

        if element_1.attrib != element_2.attrib:
            return False

        if len(element_1) != len(element_2):
            return False

        return all(self.compare_tree(c1, c2) for c1, c2 in zip(element_1, element_2))
