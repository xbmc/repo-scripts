# coding=utf-8
import os
import xbmc, xbmcaddon, xbmcvfs
import xml.etree.ElementTree as xmltree
import hashlib, hashlist
import copy
from traceback import print_exc
import simpleeval, operator, ast
from simpleeval import simple_eval

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id').decode( 'utf-8' )
SKINPATH     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')

STRINGCOMPARE = "StringCompare"
if int( xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0] ) >= 17:
    STRINGCOMPARE = "String.IsEqual"

def log(txt):
    if ADDON.getSetting( "enable_logging" ) == "true":
        try:
            if isinstance (txt,str):
                txt = txt.decode('utf-8')
            message = u'%s: %s' % (ADDONID, txt)
            xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
        except:
            pass

class Template():
    def __init__( self ):
        # Load the skins template.xml file
        templatepath = os.path.join( SKINPATH , "template.xml" )
        self.otherTemplates = []
        try:
            self.tree = xmltree.parse( templatepath )

            log( "Loaded template.xml file")

            # Pull out the names and includes of the 'other' templates - used to generate accurate progress
            # and to build empty 'other' templates if necessary
            for otherTemplate in self.tree.getroot().findall( "other" ):
                includeName = "skinshortcuts-template"
                if "include" in otherTemplate.attrib:
                    includeName = "skinshortcuts-template-%s" %( otherTemplate.attrib.get( "include" ) )
                if includeName not in self.otherTemplates:
                    self.otherTemplates.append( includeName )
            
            # Add the template.xml to the hash file
            self._save_hash( templatepath, xbmcvfs.File( templatepath ).read() )
        except:
            # We couldn't load the template.xml file
            if xbmcvfs.exists( templatepath ):
                # Unable to parse template.xml
                log( "Unable to parse template.xml. Invalid xml?" )
                self._save_hash( templatepath, xbmcvfs.File( templatepath ).read() )
            else:
                # No template.xml            
                self.tree = None
                self._save_hash( templatepath, None )
            
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
        self.simple_eval = simpleeval.SimpleEval()
        self.simple_eval.operators[ast.In] = operator.contains
            
    def parseItems( self, menuType, level, items, profile, profileVisibility, visibilityCondition, menuName, mainmenuID = None, buildOthers = False, mainmenuitems = None ):
        # This will build an item in our includes for a menu
        if self.includes is None or self.tree is None:
            return
            
        # Get the template for this menu
        if menuType == "mainmenu":
            template = self.tree.find( "mainmenu" )
            if template is not None:
                template = self.copy_tree( template )
        else:
            if len( items.findall( "item" ) ) == 0: return
            template = self.findSubmenu( menuName, level )
            
        if template is not None:
            # Found a template - let's build it
            if menuType == "mainmenu":
                log( "Main menu template found" )
            else:
                log( " - Submenu template found" )
        
            # We need to check that the relevant includes existing
            # First, the overarching include
            includeName = "skinshortcuts-template"
            if "include" in template.attrib:
                includeName += "-%s" %( template.attrib.get( "include" ) )
            
            treeRoot = self.getInclude( self.includes, includeName, profileVisibility, profile )
            includeTree = self.getInclude( self.includes, includeName + "-%s" %( profile ), None, None )

            # If we've been passed any mainmenu items, retrieve their properties
            properties = {}
            if mainmenuitems is not None:
                properties = self.getProperties( template, mainmenuitems )
            
            # Now replace all <skinshortcuts> elements with correct data
            self.replaceElements( template.find( "controls" ), visibilityCondition, profileVisibility, items, properties, customitems = template.findall( "items" ) )
            
            # Add the template to the includes
            for child in template.find( "controls" ):
                includeTree.append( child )
            
        # Now we want to see if any of the main menu items match a template
        if not buildOthers or len( self.otherTemplates ) == 0:
            return

        # If we've been passed any mainmenu items, retrieve the id of the main menu item
        rootID = None
        if mainmenuitems is not None:
            rootID = mainmenuitems.attrib.get( "id" )

        progressCount = 0
        numTemplates = 0
        if menuType == "mainmenu":
            log( "Building templates")
        else:
            # Switch menutype for level for submenu templates, to make it easier to pass in
            menuType = level
        for item in items:
            progressCount = progressCount + 1
            if menuType == "mainmenu":
                # First we need to build the visibilityCondition, based on the items
                # submenuVisibility element, and the mainmenuID
                visibilityName = ""
                for element in item.findall( "property" ):
                    if "name" in element.attrib and element.attrib.get( "name" ) == "submenuVisibility":
                        visibilityName = element.text
                        break
                
                finalVisibility = "%s(Container(%s).ListItem.Property(submenuVisibility),%s)" %( STRINGCOMPARE, mainmenuID, visibilityName )
            else:
                # First we need to build the visibilityCondition, based on the visibility condition
                # passed in, and the submenuVisibility element
                visibilityName = ""
                for element in item.findall( "property" ):
                    if "name" in element.attrib and element.attrib.get( "name" ) == "labelID":
                        visibilityName = element.text
                        break
                
                finalVisibility = "[%s + %s(Container(::SUBMENUCONTAINER::).ListItem.Property(labelID),%s)]" %( visibilityCondition, STRINGCOMPARE, visibilityName )

            # Now find a matching template - if one matches, it will be saved to be processed
            # at the end (when we have all visibility conditions)
            numTemplates += self.findOther( item, profile, profileVisibility, visibilityCondition, finalVisibility, menuType, rootID )
            if menuType == "mainmenu":
                self.progress.update( int( self.current + ( ( float( self.percent ) / float( len( items ) ) ) * progressCount ) ) )
        if numTemplates != 0:
            log( " - %d templates" %( numTemplates ) )
                    
    def writeOthers( self ):
        # This will write any 'other' elements we have into the includes file
        # (now we have all the visibility conditions for them)
        if self.includes is None or self.tree is None:
            return
        
        if len( self.finalize ) == 0:
            return

        finalVariables = {}
        finalVariableNames = []
            
        for template in self.finalize:
            # Get the group name
            name = "skinshortcuts-template"
            if "include" in template.attrib:
                includeName = template.attrib.get( "include" )
                name += "-%s" %( includeName )
                # Remove the include from our list of other templates, as we don't need to build an empty one
                if name in self.otherTemplates:
                    self.otherTemplates.remove( name )
            
            # Loop through any profiles we have
            for profile in template.findall( "skinshortcuts-profile" ):
                visibilityCondition = None
                # Build the visibility condition
                for condition in profile.findall( "visible" ):
                    if visibilityCondition is None:
                        visibilityCondition = condition.text
                    elif condition.text != "":
                        visibilityCondition += " | " + condition.text
                
                # Get the include this will be done under
                root = self.getInclude( self.includes, name, profile.attrib.get( "visible" ), profile.attrib.get( "profile" ) )
                include = self.getInclude( self.includes, "%s-%s" %( name, profile.attrib.get( "profile" ) ), None, None ) #profile.attrib.get( "visible" ) )
                
                # Create a copy of the node with any changes within (this time it'll be visibility)
                final = self.copy_tree( template )
                self.replaceElements( final, visibilityCondition, profile.attrib.get( "visible" ), [] )
                
                # Add the template to the includes
                controls = final.find( "controls" )
                if controls is not None:
                    for child in controls:
                        include.append( child )

                # Process the variables
                variables = final.find( "variables" )
                if variables is not None:
                    for variable in variables.findall( "variable" ):
                        # If the profile doesn't have a dict in finalVariables, create one
                        profileVisibility = profile.attrib.get( "visible" )
                        if profileVisibility not in finalVariables.keys():
                            finalVariables[ profileVisibility ] = {}

                        # Save the variable name
                        varName = variable.attrib.get( "name" )
                        if varName not in finalVariableNames:
                            finalVariableNames.append( varName )

                        # Get any existing values for this profile + variable
                        newVariables = []
                        if varName in finalVariables[ profileVisibility ].keys():
                            newVariables = finalVariables[ profileVisibility ][ varName ]

                        # Loop through new values provided by this template
                        for value in variable.findall( "value" ):
                            condition = ""
                            if "condition" in value.attrib:
                                condition = value.attrib.get( "condition" )

                            # Add the new condition/value pair only if it really is new
                            newValue = ( condition, value.text )
                            if newValue not in newVariables:
                                newVariables.append( newValue )

                        # Add the values into the dict
                        finalVariables[ profileVisibility ][ varName ] = newVariables

        # And now write the variables
        for variableName in finalVariableNames:
            element = xmltree.SubElement( self.includes, "variable" )
            element.set( "name", variableName )
            for condition, value in self.parseVariables( variableName, finalVariables ):
                valueElement = xmltree.SubElement( element, "value" )
                valueElement.text = value
                if condition != "":
                    valueElement.set( "condition", condition )

        # If there are any 'other' templates that we haven't built, build an empty one
        for otherTemplate in self.otherTemplates:
            # Get the include this will be built in
            root = self.getInclude( self.includes, otherTemplate, None, None )
            xmltree.SubElement( root, "description" ).text = "This include was built automatically as the template didn't match any menu items"

    def parseVariables( self, variableName, allVariables ):
        # This function will return all condition/value elements for a given variable, including adding profile conditions
        returnVariables = []
        noCondition = []

        # Firstly, lets pull out the specific variables from all the variables we've been passed
        limitedVariables = {}
        for profile in allVariables:
            if variableName in allVariables[ profile ].keys():
                limitedVariables[ profile ] = allVariables[ profile ][ variableName ]

        numProfiles = len( limitedVariables )

        for profile in limitedVariables:
            while len( limitedVariables[ profile ] ) != 0:
                # Grab the first value from the list
                value = limitedVariables[ profile ].pop( 0 )
                profiles = [ profile ]

                # Now check if any other profile has that value
                for additionalProfile in limitedVariables:
                    if value in limitedVariables[ additionalProfile ]:
                        # It does - remove it and add the profile visibility to the one we already have
                        profiles.append( additionalProfile )
                        limitedVariables[ additionalProfile ].remove( value )

                # Check if we need to add profile visibility
                if len( profiles ) == numProfiles:
                    # We don't
                    if value[ 0 ] == "":
                        noCondition.append( value )
                    else:
                        returnVariables.append( value )
                else:
                    # We do
                    condition = None
                    for profileVisibility in profiles:
                        if condition is None:
                            condition = profileVisibility
                        else:
                            condition = "%s | %s" %( condition, profileVisibility )
                    if value[ 0 ] == "":
                        noCondition.append( ( condition, value[ 1 ] ) )
                    else:
                        returnVariables.append( ( "%s + [%s]" %( condition, value[ 0 ] ), value[ 1 ] ) )

        return returnVariables + noCondition
            
    def getInclude( self, tree, name, condition, profile ):
        # This function gets an existing <include/>, or creates it
        for include in tree.findall( "include" ):
            if include.attrib.get( "name" ) == name:
                if condition is None:
                    return include
                    
                # We've been passed a condition, check there's an include with that
                # as condition and name as text
                for visInclude in include.findall( "include" ):
                    if visInclude.attrib.get( "condition" ) == condition:
                        return include
                        
                # We didn't find condition,so create it
                visInclude = xmltree.SubElement( include, "include" )
                visInclude.set( "condition", condition )
                visInclude.text = name + "-" + profile
                
                return include
        
        # We didn't find the node, so create it
        newInclude = xmltree.SubElement( tree, "include" )
        newInclude.set( "name", name )
        
        # If we've been passed a condition, create an include with that as condition
        # and name as text
        if condition is not None:
            visInclude = xmltree.SubElement( newInclude, "include" )
            visInclude.set( "condition", condition )
            visInclude.text = name + "-" + profile
        
        return newInclude
        
        
    def findSubmenu( self, name, level ):
        # Find the correct submenu template
        returnElem = None
        for elem in self.tree.findall( "submenu" ):
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
                if elem.attrib.get( "level" ) != str( level ):
                    continue
            # If there's a name attrib, check if it matches
            if "name" in elem.attrib:
                if elem.attrib.get( "name" ) == name:
                    # This is the one we want :)
                    return self.copy_tree( elem )
                else:
                    continue
            # Save this, in case we don't find a better match
            returnElem = elem

        if returnElem is None: return None            
        return self.copy_tree( returnElem )
        
    def findOther( self, item, profile, profileVisibility, simpleVisibility, visibilityCondition, menuType, rootID ):
        # Find a template matching the item we have been passed
        foundTemplateIncludes = []
        numTemplates = 0
        searchType = "other"
        if menuType != "mainmenu":
            searchType = "submenuOther"
        for elem in self.tree.findall( searchType ):
            # Check that we don't already have a template for this include
            includeName = None
            if "include" in elem.attrib:
                includeName = elem.attrib.get( "include" )
            if includeName in foundTemplateIncludes:
                continue

            template = self.copy_tree( elem )
            matched = True

            finalVisibility = visibilityCondition
            if menuType != "mainmenu":
                # This isn't the main menu

                # First we check if the level matches
                if "level" in elem.attrib:
                    if menuType != int( elem.attrib.get( "level" ) ):
                        matched = False
                        continue
                elif menuType != 0:
                    matched = False
                    continue
                
                # Next we either extend the visibility condition to also match the submenu
                # (if the template provides the submenu container ID), or drop the visibility condition
                if "container" in elem.attrib:
                    finalVisibility = visibilityCondition.replace( "::SUBMENUCONTAINER::", elem.attrib.get( "container" ) )
                else:
                    finalVisibility = simpleVisibility

            # Check whether the skinner has set the match type (whether all conditions need to match, or any)
            matchType = "all"
            matchElem = template.find( "match" )
            if matchElem is not None:
                matchType = matchElem.text.lower()
                if matchType not in [ "any", "all" ]:
                    log( "Invalid <match /> element in template" )
                    matchType = "all"
                elif matchType == "any":
                    matched = False
            
            # Check the conditions
            for condition in template.findall( "condition" ):
                if matchType == "all":
                    if matched == False:
                        break
                    if self.checkCondition( condition, item ) == False:
                        matched = False
                        break
                else:
                    if matched == True:
                        break
                    if self.checkCondition( condition, item ) == True:
                        matched = True
                        break

                
            # If the conditions didn't match, we're done here
            if matched == False:
                continue

            numTemplates += 1
                
            # All the rules matched, so next we'll get any properties
            properties = self.getProperties( template, item )
            if rootID is not None:
                properties[ "auto-rootID" ] = rootID
            
            # Next up, we do any replacements - EXCEPT for visibility, which
            # we'll store for later (in case multiple items would have an
            # identical template
            self.replaceElements( template.find( "controls" ), None, None, [], properties )
            self.replaceElements( template.find( "variables" ), None, None, [], properties )
            
            # Now we need to check if we've already got a template identical to this
            textVersion = None
            foundInPrevious = False
            for previous in self.finalize:
                # Check that the previous template uses the same include
                includeNameCheck = includeName
                if includeName is None:
                    includeNameCheck = "NONE"
                if previous.find( "skinshortcuts-includeName" ).text != includeNameCheck:
                    continue
                    
                # Compare templates
                if self.compare_tree( template.find( "controls" ), previous.find( "controls" ) ) and self.compare_tree( template.find( "variables" ), previous.find( "variables" ) ) :
                    # They are the same
                    
                    # Add our details to the previous version, so we can build it
                    # with full visibility details later
                    for profileMatch in previous.findall( "skinshortcuts-profile" ):
                        if profileMatch.attrib.get( "profile" ) == profile:
                            # Check if we've already added this visibilityCondition
                            for visible in profileMatch.findall( "visible" ):
                                if visible.text == finalVisibility:
                                    # The condition is already there
                                    foundInPrevious = True
                            
                            # We didn't find it, so add it
                            xmltree.SubElement( profileMatch, "visible" ).text = finalVisibility
                            foundInPrevious = True

                    if foundInPrevious == True:
                        break
                            
                    # We didn't find this profile, so add it
                    newElement = xmltree.SubElement( previous, "skinshortcuts-profile" )
                    newElement.set( "profile", profile )
                    newElement.set( "visible", profileVisibility )
                    
                    # And save the visibility condition
                    xmltree.SubElement( newElement, "visible" ).text = finalVisibility
                    
                    # And we're done
                    foundTemplateIncludes.append( includeName )
                    foundInPrevious = True

            if foundInPrevious == False:
                # We don't have this template saved, so add our profile details to it
                newElement = xmltree.SubElement( template, "skinshortcuts-profile" )
                newElement.set( "profile", profile )
                newElement.set( "visible", profileVisibility )

                # Save the visibility condition
                xmltree.SubElement( newElement, "visible" ).text = finalVisibility

                newElement = xmltree.SubElement( template, "skinshortcuts-includeName" )
                if includeName is None:
                    newElement.text = "NONE"
                else:
                    newElement.text = includeName
                
                # Add it to our finalize list
                self.finalize.append( template )

                # Add that we've found a template for this include
                foundTemplateIncludes.append( includeName )

        return numTemplates
            
    def checkCondition( self, condition, items ):
        # Check if a particular condition is matched for an 'other' template
        if "tag" not in condition.attrib:
            # Tag attrib is required
            return False
        else:
            tag = condition.attrib.get( "tag" )
            
        attrib = None
        if "attribute" in condition.attrib:
            attrib = condition.attrib.get( "attribute" ).split( "|" )
            
        # Find all elements with matching tag
        matchedRule = False
        for item in items.findall( tag ):
            if attrib is not None:
                if attrib[ 0 ] not in item.attrib:
                    # Doesn't have the attribute we're looking for
                    continue
                if attrib[ 1 ] != item.attrib.get( attrib[ 0 ] ):
                    # This property doesn't match
                    continue
                    
            if condition.text is not None and item.text != condition.text:
                # This property doesn't match
                continue
            
            # The rule has been matched :)
            return True
            
        return False
        
    def getProperties( self, elem, items ):
        # Get any properties specified in an 'other' template
        properties = {}

        # Start by finding all properties defined directly in the template
        searchProperties = elem.findall( "property" )

        # Add any properties defined in a property group
        for propertyGroup in elem.findall( "propertyGroup" ):
            for searchGroup in self.tree.findall( "propertyGroup" ):
                if propertyGroup.text.lower() == searchGroup.attrib.get( "name" ).lower():
                    searchProperties += searchGroup.findall( "property" )

        # Loop through all the properties
        for property in searchProperties:
            if "name" not in property.attrib or property.attrib.get( "name" ) in properties:
                # Name attrib required, or we've already got a property with this name
                continue
            name = property.attrib.get( "name" )

            # Pull out the tag, attribute and value attribs into an array of tuples
            rules = []
            matchAny = True
            propertyValue = None
            if "propertyValue" in property.attrib:
                propertyValue = property.attrib.get( "propertyValue" )
            
            # Check for multiple items to match against this single value
            for singleMatch in property.findall( "rule" ):
                tag = None
                attribute = None
                value = None
                if "tag" in singleMatch.attrib:
                    tag = singleMatch.attrib.get( "tag" )
                else:
                    # Tag is required, so we'll pass on this
                    log( "Trying to match a property without using a tag element" )
                    continue
                if "attribute" in singleMatch.attrib:
                    attribute = singleMatch.attrib.get( "attribute" ).split( "|" )
                if "value" in singleMatch.attrib:
                    value = singleMatch.attrib.get( "value" ).split( "|" )
                rules.append( ( tag, attribute, value, propertyValue ) )

            matchAll = property.find( "match" )
            if matchAll is not None and matchAll.text.lower() == "all":
                matchAny = False

            # If we haven't grabbed anything to match against yet
            if len( rules ) == 0:
                if "tag" in property.attrib:
                    tag = property.attrib.get( "tag" )

                    # Special case for the ID of the main menu item
                    if tag.lower() == "mainmenuid":
                        properties[ name ] = items.attrib.get( "id" )
                        continue

                    # Pull out the properties we'll match against
                    attribute = None
                    value = None
                    propertyValue = None
                    if "attribute" in property.attrib:
                        attribute = property.attrib.get( "attribute" ).split( "|" )
                    if "value" in property.attrib:
                        value = property.attrib.get( "value" ).split( "|" )
                    if property.text:
                        propertyValue = property.text
                    rules.append( ( tag, attribute, value, propertyValue ) )
                else:
                    # No tag property, so this will always match (so let's just use it!)
                    if property.text:
                        properties[ name ] = property.text
                    else:
                        properties[ name ] = ""
                    continue

            if matchAny:
                # Match the property if any of the rules match
                matchedRule = False
                for rule in rules:
                    if matchedRule:
                        break

                    # Let's get looking for any items that match
                    tag = rule[ 0 ]
                    attrib = rule[ 1 ]
                    value = rule[ 2 ]
                    
                    for item in items.findall( tag ):
                        if attrib is not None:
                            if attrib[ 0 ] not in item.attrib:
                                # Doesn't have the attribute we're looking for
                                continue
                            if attrib[ 1 ] != item.attrib.get( attrib[ 0 ] ):
                                # The attributes value doesn't match
                                continue

                        if not item.text:
                            # The item doesn't have a value to match
                            continue
                                
                        if value is not None and item.text not in value:
                            # The value doesn't match
                            continue
                            
                        # We've matched a property :)
                        if rule[ 3 ] is not None:
                            properties[ name ] = rule[ 3 ]
                        else:
                            properties[ name ] = item.text
                        break

            else:
                # Match the property only if all the rules match
                matchedRule = True
                for rule in rules:
                    if not matchedRule:
                        break

                    # Let's get looking for any items that match
                    tag = rule[ 0 ]
                    attrib = rule[ 1 ]
                    value = rule[ 2 ]
                    
                    for item in items.findall( tag ):
                        log( repr( attrib ) )
                        if attrib is not None:
                            if attrib[ 0 ] not in item.attrib:
                                # Doesn't have the attribute we're looking for
                                matchedRule = False
                                continue
                            if attrib[ 1 ] != item.attrib.get( attrib[ 0 ] ):
                                # The attributes value doesn't match, so we don't want to check the rule against it
                                continue

                        if not item.text:
                            # The item doesn't have a value to match
                            matchedRule = False
                            continue
                                
                        if value is not None and item.text not in value:
                            # The value doesn't match
                            matchedRule = False
                            continue
                            
                if matchedRule:
                    # We've matched a property :)
                    if rule[ 3 ] is not None:
                        properties[ name ] = rule[ 3 ]
                    else:
                        # This method only supports setting the property value directly, so if it wasn't specified,
                        # include a log error
                        log( "Invalid template - cannot set property directly to menu item elements value when using multiple rules for single property")
        
        return properties

    def combineProperties( self, elem, items, currentProperties ):
        # Combines an existing set of properties with additional properties
        newProperties = self.getProperties( elem, items )
        for propertyName in newProperties:
            if propertyName in currentProperties.keys():
                continue
            currentProperties[ propertyName ] = newProperties[ propertyName ]

        return currentProperties  
    
    def replaceElements( self, tree, visibilityCondition, profileVisibility, items, properties = {}, customitems = None ):
        if tree is None: return
        for elem in tree:
            # <tag skinshortcuts="visible" /> -> <tag condition="[condition]" />
            if "skinshortcuts" in elem.attrib:
                # Get index of the element
                index = list( tree ).index( elem )
                
                # Get existing attributes, text and tag
                attribs = []
                for singleAttrib in elem.attrib:
                    if singleAttrib == "skinshortcuts":
                        type = elem.attrib.get( "skinshortcuts" )
                    else:
                        attribs.append( ( singleAttrib, elem.attrib.get( singleAttrib ) ) )
                text = elem.text
                tag = elem.tag
                
                # Don't continue is type = visibility, and no visibilityCondition
                if type == "visibility" and visibilityCondition is None:
                    continue
                
                # Remove the existing element
                tree.remove( elem )
                
                # Make replacement element
                newElement = xmltree.Element( tag )
                if text is not None:
                    newElement.text = text
                for singleAttrib in attribs:
                    newElement.set( singleAttrib[ 0 ], singleAttrib[ 1 ] )
                    
                # Make replacements
                if type == "visibility" and visibilityCondition is not None:
                    newElement.set( "condition", visibilityCondition )
                    
                # Insert it
                tree.insert( index, newElement )
            
            # <tag>$skinshortcuts[var]</tag> -> <tag>[value]</tag>
            # <tag>$skinshortcuts[var]</tag> -> <tag><include>[includeName]</include></tag> (property = $INCLUDE[includeName])
            if elem.text is not None:
                while "$SKINSHORTCUTS[" in elem.text:
                    # Split the string into its composite parts
                    stringStart = elem.text.split( "$SKINSHORTCUTS[", 1 )
                    stringEnd = stringStart[ 1 ].split( "]", 1 )
                    # stringStart[ 0 ] = Any code before the $SKINSHORTCUTS property
                    # StringEnd[ 0 ] = The name of the $SKINSHORTCUTS property
                    # stringEnd[ 1 ] = Any code after the $SKINSHORTCUTS property

                    if stringEnd[ 0 ] in properties:
                        if properties[ stringEnd[ 0 ] ].startswith( "$INCLUDE[" ):
                            # Remove text property
                            elem.text = ""
                            # Add include element
                            includeElement = xmltree.SubElement( elem, "include" )
                            includeElement.text = properties[ stringEnd [ 0 ] ][ 9:-1 ]
                        else:
                            elem.text = stringStart[ 0 ] + properties[ stringEnd[ 0 ] ] + stringEnd[ 1 ]
                    else:
                        elem.text = stringStart[ 0 ] + stringEnd[ 1 ]
            
            # <tag attrib="$skinshortcuts[var]" /> -> <tag attrib="[value]" />
            for attrib in elem.attrib:
                value = elem.attrib.get( attrib )
                while "$SKINSHORTCUTS[" in elem.attrib.get( attrib ):
                    # Split the string into its composite parts
                    stringStart = elem.attrib.get( attrib ).split( "$SKINSHORTCUTS[", 1 )
                    stringEnd = stringStart[ 1 ].split( "]", 1 )

                    if stringEnd[ 0 ] in properties:
                        elem.set( attrib, stringStart[ 0 ] + properties[ stringEnd[ 0 ] ] + stringEnd[ 1 ] )
                    else:
                        elem.set( attrib, stringStart[ 0 ] + stringEnd[ 1 ] )

                if value.startswith( "$SKINSHORTCUTS[" ) and value[ 15:-1 ] in properties:
                    newValue = ""
                    if value[ 15:-1 ] in properties:
                        newValue = properties[ value[ 15:-1 ] ]
                    elem.set( attrib, newValue )

            # <tag>$PYTHON[var]</tag> -> <tag>[result]</tag>
            if elem.text is not None:
                while "$PYTHON[" in elem.text:
                    # Split the string into its composite parts
                    stringStart = elem.text.split( "$PYTHON[", 1 )
                    stringEnd = stringStart[ 1 ].split( "]", 1 )
                    # stringStart[ 0 ] = Any code before the $MATHS property
                    # StringEnd[ 0 ] = The maths to be performed
                    # stringEnd[ 1 ] = Any code after the $MATHS property

                    stringEnd[ 0 ] = simple_eval( "%s" %( stringEnd[ 0 ] ), names=properties )
                    
                    elem.text = stringStart[ 0 ] + str( stringEnd[ 0 ] ) + stringEnd[ 1 ]
            
            # <tag attrib="$PYTHON[var]" /> -> <tag attrib="[value]" />
            for attrib in elem.attrib:
                value = elem.attrib.get( attrib )
                while "$PYTHON[" in elem.attrib.get( attrib ):
                    # Split the string into its composite parts
                    stringStart = elem.attrib.get( attrib ).split( "$PYTHON[", 1 )
                    stringEnd = stringStart[ 1 ].split( "]", 1 )

                    stringEnd[ 0 ] = simple_eval( "%s" %( stringEnd[ 0 ] ), names=properties )

                    elem.set( attrib, stringStart[ 0 ] + str( stringEnd[ 0 ] ) + stringEnd[ 1 ] )
            
            # <skinshortcuts>visible</skinshortcuts> -> <visible>[condition]</visible>
            # <skinshortcuts>items</skinshortcuts> -> <item/><item/>...
            if elem.tag == "skinshortcuts":
                # Get index of the element
                index = list( tree ).index( elem )
                
                # Get the type of replacement
                type = elem.text
                
                # Don't continue is type = visibility, and no visibilityCondition
                if type == "visibility" and visibilityCondition is None:
                    continue
                
                # Remove the existing element
                tree.remove( elem )
                
                # Make replacements
                if type == "visibility" and visibilityCondition is not None:
                    # Create a new visible element
                    newelement = xmltree.Element( "visible" )
                    newelement.text = visibilityCondition
                    # Insert it
                    tree.insert( index, newelement )
                elif type == "items" and customitems is not None and elem.attrib.get( "insert" ):
                    for elem in self.buildSubmenuCustomItems( customitems, items.findall( "item" ), elem.attrib.get( "insert" ), properties ):
                        for child in elem:
                            tree.insert( index, child )
                elif type == "items":
                    # Firstly, go through and create an array of all items in reverse order, without
                    # their existing visible element, if it matches our visibilityCondition
                    newelements = []
                    if items == []:
                        break
                    for item in items.findall( "item" ):
                        newitem = self.copy_tree( item )

                        # Remove the existing visible elem from this
                        for visibility in newitem.findall( "visible" ):
                            if visibility.text != profileVisibility:
                                continue
                            newitem.remove( visibility )
                        
                        # Add a copy to the array
                        newelements.insert( 0, newitem )
                    if len( newelements ) != 0:
                        for elem in newelements:
                            # Insert them into the template
                            tree.insert( index, elem )

            else:
                # Iterate through tree
                self.replaceElements( elem, visibilityCondition, profileVisibility, items, properties, customitems = customitems )

    def buildSubmenuCustomItems( self, template, items, insert, currentProperties ):
        # Builds an 'items' template within a submenu template

        # Find the template with the correct insert attribute
        itemTemplate = None
        for testTemplate in template:
            if testTemplate.attrib.get( "insert" ) == insert:
                itemTemplate = testTemplate
                break

        if itemTemplate is None:
            # Couldn't find a template
            return []

        newelements = []
        for item in items:
            newElement = self.copy_tree( itemTemplate.find( "controls" ) )
            self.replaceElements( newElement, None, None, [], self.combineProperties( itemTemplate, item, currentProperties.copy() ) )
            newelements.insert( 0, newElement )
        return newelements
            
    def _save_hash( self, filename, file ):
        if file is not None:
            hasher = hashlib.md5()
            hasher.update( file )
            hashlist.list.append( [filename, hasher.hexdigest()] )
        else:
            hashlist.list.append( [filename, None] )            

    def copy_tree( self, elem ):
        if elem is None: return None
        ret = xmltree.Element(elem.tag, elem.attrib)
        ret.text = elem.text
        ret.tail = elem.tail
        for child in elem:
            ret.append(self.copy_tree(child))
        return ret

    def compare_tree( self, e1, e2 ):
        if e1 is None and e2 is None:
            return True
        if e1 is None or e2 is None:
            return False
        if e1.tag != e2.tag: return False
        if e1.text != e2.text: return False
        if e1.tail != e2.tail: return False
        if e1.attrib != e2.attrib: return False
        if len(e1) != len(e2): return False
        return all(self.compare_tree(c1, c2) for c1, c2 in zip(e1, e2))
