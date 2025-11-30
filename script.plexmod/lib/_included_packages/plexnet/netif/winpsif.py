# coding=utf-8

import subprocess
import re
import sys

PS_RE = re.compile(r'(?mu)^Description\s+: (?P<name>[^\n]+)\nIPAddress\s+: {(?P<addr>[0-9.]+),'
                   r'.+\nIPSubnet\s+: {(?P<subnet>[0-9.]+),.+\n')


def getInterfaces():
    """
    Use powershell to retrieve interfaces; parse using PS_RE, returning tuples of (name, ipaddress, subnet)
    """
    kwa = {}
    if sys.version_info[0] >= 3:
        kwa = {"encoding": "windows-1252"}

    return PS_RE.findall(subprocess.check_output(
        'powershell "Get-WmiObject -Class Win32_NetworkAdapterConfiguration | '
        'Select-Object Description, IPAddress, IPSubnet | Format-List"',
        shell=True, **kwa))
