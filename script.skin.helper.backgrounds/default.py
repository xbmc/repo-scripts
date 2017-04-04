#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.backgrounds
    If called as script provides a dialog to configure conditional backgrounds
'''

from resources.lib.conditional_backgrounds import ConditionalBackgrounds
DIALOG = ConditionalBackgrounds("DialogSelect.xml", "")
DIALOG.doModal()
del DIALOG
