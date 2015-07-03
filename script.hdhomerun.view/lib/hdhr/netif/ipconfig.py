# -*- coding: utf-8 -*-

import subprocess

def parse(data=None):
    data = data or subprocess.check_output('ipconfig /all',startupinfo=getStartupInfo())
    dlist = [d.rstrip() for d in data.split('\n')]
    mode = None
    sections = []
    while dlist:
        d = dlist.pop(0)
        if not d:
            if mode == 'HEADING':
                mode = 'DATA'
            else:
                mode = 'HEADING'
            continue
        elif mode == 'HEADING':
            sections.append({'name':d.strip('.: ')})
        elif mode == 'DATA':
            if d.endswith(':'):
                k = d.strip(':. ')
                mode = 'VALUE:' + k
                sections[-1][k] = ''
            else:
                k,v = d.split(':',1)
                k = k.strip(':. ')
                mode = 'VALUE:' + k
                v = v.replace('(Preferred)','')
                sections[-1][k] = v.strip()
        elif mode and mode.startswith('VALUE:'):
            if not d.startswith('        '):
                mode = 'DATA'
                dlist.insert(0,d)
                continue
            k = mode.split(':',1)[-1]
            v = d.replace('(Preferred)','')
            sections[-1][k] += ',' + v.strip()
    return sections[1:]

def getStartupInfo():
    if hasattr(subprocess,'STARTUPINFO'): #Windows
        startupinfo = subprocess.STARTUPINFO()
        try:
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW #Suppress terminal window
        except:
            startupinfo.dwFlags |= 1
        return startupinfo

    return None