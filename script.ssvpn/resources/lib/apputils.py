#/*
# *
# * OpenVPN for Kodi.
# *
# * Copyright (C) 2018 Venus
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.
# *
# */

import os
import subprocess
import kodisettings
import kodiutils
import vici

settings = kodisettings.KodiSettings()

conf_path = settings.get_datapath('ipsec.conf')
secret_path = settings.get_datapath('ipsec.secrets')

conn_name = "kodi"

update_resolve_script = "/etc/openvpn/update-resolv-conf.sh"

def display_notification(text, subtext=False):
    image = settings.get_path('icon.png')
    if subtext:
        text = text + ': ' + subtext
    kodiutils.notification(settings.get_name(), text, image=image)

def log_debug(msg):
    if settings['debug'] == 'true':
        print 'script.ssvpn: DEBUG: %s' % msg

def log_error(msg):
    print 'script.ssvpn: ERROR: %s' % msg

# run bash command with sudo permission
def run_cmd_with_sudo(cmd, sudopassword):
    # log_debug("run command: " + cmd)
    if settings['sudo'] == 'true':
        run_cmd = 'echo \'%s\' | sudo -S %s' % (sudopassword, cmd)
    else:
        run_cmd = 'sudo %s' % (cmd)

    process = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE)

# enable/disable all ipv6 interfaces
# if status is true, all ipv6 interfaces are disabled
# if status is fales, all ipv6 interfaces are enabled
def setup_ipv6_interfaces(status, sudopassword):
    if settings['ipv6'] == 'true':
        if status:
            cmdline = "echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6"
            run_cmd_with_sudo(cmdline, sudopassword)
        else:
            cmdline = "echo 0 > /proc/sys/net/ipv6/conf/all/disable_ipv6"
            run_cmd_with_sudo(cmdline, sudopassword)

# apply iptables rules for killswitch function
def apply_killswitch(ipaddr, sudopassword):
    if settings['killswitch'] == 'true':
        # allow access for the interfaces loopback, tun, and tap
        run_cmd_with_sudo("iptables -A OUTPUT -o tun+ -j ACCEPT", sudopassword)
        run_cmd_with_sudo("iptables -A OUTPUT -o lo+ -j ACCEPT", sudopassword)
        run_cmd_with_sudo("iptables -A OUTPUT -s 10.0.0.0/8 -j ACCEPT", sudopassword)

        if settings['allow_local'] == 'true':
            local_networks = settings.get_datapath('localnetworks')

            fp = open(local_networks, "r")
            networks = fp.readlines()
            for network in networks:
                run_cmd_with_sudo("iptables -A OUTPUT -d " + network.rstrip() + " -j ACCEPT", sudopassword)

            fp.close()

        # allow connections to certain IP addresses with no active VPN
        run_cmd_with_sudo("iptables -A OUTPUT -d " + ipaddr + " -j ACCEPT", sudopassword)

        # block all disallowed connections
        run_cmd_with_sudo("iptables -A OUTPUT -j DROP", sudopassword)

# clean iptables rules for killswitch function
def clean_killswitch(ipaddr, sudopassword):
    if settings['killswitch'] == 'true':
        run_cmd_with_sudo("iptables -D OUTPUT -j DROP", sudopassword)

        if settings['allow_local'] == 'true':
            local_networks = settings.get_datapath('localnetworks')

            fp = open(local_networks, "r")
            networks = fp.readlines()
            for network in networks:
                run_cmd_with_sudo("iptables -D OUTPUT -d " + network.rstrip() + " -j ACCEPT", sudopassword)

            fp.close()

        run_cmd_with_sudo("iptables -D OUTPUT -o tun+ -j ACCEPT", sudopassword)
        run_cmd_with_sudo("iptables -D OUTPUT -o lo+ -j ACCEPT", sudopassword)
        run_cmd_with_sudo("iptables -D OUTPUT -s 10.0.0.0/8 -j ACCEPT", sudopassword)

        run_cmd_with_sudo("iptables -D OUTPUT -d " + ipaddr + " -j ACCEPT", sudopassword)

# create openvpn authentication file
def create_auth_file(jsonObj):
    authPath = settings.get_datapath('authfile')
    fp = open(authPath, "w+")
    fp.write(jsonObj['login'] + "\n")
    fp.write(jsonObj['password'])
    fp.close()

# create openvpn config file for selected server
def create_ovpn_config(ipaddr, sudopassword):
    cmdline = "cp -f " + settings.get_path('bin/update-resolv-conf.sh') + " " + update_resolve_script
    run_cmd_with_sudo(cmdline, sudopassword)

    cmdline = "chmod +x " + update_resolve_script
    run_cmd_with_sudo(cmdline, sudopassword)

    tmpFile = settings.get_path('data/config.ovpn')
    configPath = settings.get_datapath('config.ovpn')

    tmpFp = open(tmpFile, "r")
    configFp = open(configPath, "w+")

    configContent = tmpFp.readlines()
    for line in configContent:
        if line.startswith('remote '):
            line = "remote " + ipaddr + " 443 udp\n"
        if line.startswith('auth-user-pass'):
            line = "auth-user-pass authfile\n"
        if line.startswith('block-outside-dns'):
            line = ""

        configFp.write(line)

    updateDNSContent = """setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
script-security 2
up """ + update_resolve_script + """
down """ + update_resolve_script + """
down-pre"""

    configFp.write(updateDNSContent)

    configFp.close()
    tmpFp.close()

# create openvpn status file
def create_status_file(ipaddr):
    statusFile = settings.get_datapath('connected')
    fp = open(statusFile, "w+")
    fp.write(ipaddr)
    fp.close()

# get connected server ip from openvpn status file
def get_connected_ip():
    statusFile = settings.get_datapath('connected')
    if os.path.exists(statusFile):
        fp = open(statusFile, "r")
        ipaddr = fp.read()
        fp.close()
        return ipaddr
    else:
        return ""

def create_ipsec_conf(username, hostname):
    log_debug("creating ipsec config file")

    fp = open(conf_path, "w+")
    conf_content = """conn """ + conn_name + """
        right=""" + str(hostname) + """
        rightid=%""" + str(hostname) + """
        rightsubnet=0.0.0.0/0
        rightauth=pubkey
        leftsourceip=%config
        leftid=""" + str(username) + """
        leftauth=eap-mschapv2
        eap_identity=%identity
        auto=add"""
    fp.write(conf_content)
    fp.close()

def create_ipsec_secrets(username, password):
    log_debug("creating ipsec secrets file")
    fp = open(secret_path, "w+")
    fp.write(str(username) + " : EAP \"" + str(password) + "\"")
    fp.close()

def config_ipsec(sudopassword):
    # copy ipsec.conf, ipsec.secrets to /etc folder
    cmdline = "cp -f " + conf_path + " /etc/ipsec.conf"
    run_cmd_with_sudo(cmdline, sudopassword)

    cmdline = "cp -f " + secret_path + " /etc/ipsec.secrets"
    run_cmd_with_sudo(cmdline, sudopassword)

    # config charon constraints.conf
    cmdline = "sed -i 's/load = yes/load = no/g' /etc/strongswan.d/charon/constraints.conf"
    run_cmd_with_sudo(cmdline, sudopassword)

    # configure cacerts folder
    cmdline = "rm -rf /etc/ipsec.d/cacerts"
    run_cmd_with_sudo(cmdline, sudopassword)
    cmdline = "ln -s /etc/ssl/certs /etc/ipsec.d/cacerts"
    run_cmd_with_sudo(cmdline, sudopassword)

    # copy ca file to cacerts folder
    cmdline = "cp -f " + settings.get_path('data/vpnbrand.pem') + " /etc/ssl/certs/"
    run_cmd_with_sudo(cmdline, sudopassword)


def reload_ipsec(sudopassword):
    log_debug("reload ipsec service")
    cmdline = "ipsec restart"
    run_cmd_with_sudo(cmdline, sudopassword)

def connection_up(sudopassword):
    log_debug("ipsec connection up : " + conn_name)
    cmdline = "ipsec up " + conn_name
    run_cmd_with_sudo(cmdline, sudopassword)

def connection_down(sudopassword):
    log_debug("ipsec connection down : " + conn_name)
    cmdline = "ipsec down " + conn_name
    run_cmd_with_sudo(cmdline, sudopassword)

def check_vpn_connection():
    session = vici.Session()
    conn_state = ""

    for vpn_conn in session.list_sas():
        conn_state = vpn_conn[conn_name]['state']

    return conn_state

def get_connections():
    session = vici.Session()
    available_connections = []

    for conn in session.list_conns():
        for key in conn:
            available_connections.append(key)

    return available_connections
