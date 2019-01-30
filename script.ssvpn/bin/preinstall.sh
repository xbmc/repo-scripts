#!/bin/bash

# install openvpn
cp -rf $1/openvpn/openvpn /usr/sbin/openvpn
chmod +x /usr/sbin/openvpn
mkdir -p /usr/lib/x86_64-linux-gnu/openvpn/plugins/
cp -rf $1/openvpn/plugins/* /usr/lib/x86_64-linux-gnu/openvpn/plugins/
mkdir -p /etc/openvpn
cp -rf $1/openvpn/update-resolv-conf.sh /etc/openvpn/

#install resolvconf
cp -rf $1/resolvconf/etc/resolvconf/ /etc/
cp -rf $1/resolvconf/sbin/resolvconf /sbin/resolvconf
chmod +x /sbin/resolvconf
cp -rf $1/resolvconf/lib/* /lib/

#install ipsec
cp -rf $1/ipsec/sbin/ipsec /usr/sbin/ipsec
chmod +x /usr/sbin/ipsec
cp -rf $1/ipsec/lib/* /usr/lib/
chmod -R +x /usr/lib/ipsec/*
cd /usr/lib/ipsec/
ln -sf libcharon.so.0.0.0 libcharon.so
ln -sf libcharon.so.0.0.0 libcharon.so.0
ln -sf libsimaka.so.0.0.0 libsimaka.so
ln -sf libsimaka.so.0.0.0 libsimaka.so.0
ln -sf libstrongswan.so.0.0.0 libstrongswan.so
ln -sf libstrongswan.so.0.0.0 libstrongswan.so.0
ln -sf libtls.so.0.0.0 libtls.so
ln -sf libtls.so.0.0.0 libtls.so.0
ln -sf libvici.so.0.0.0 libvici.so
ln -sf libvici.so.0.0.0 libvici.so.0
cp -rf $1/ipsec/libexec/* /usr/libexec/
chmod +x /usr/libexec/ipsec/*
cp -rf $1/ipsec/etc/* /etc/
cp -rf $1/ipsec/systemd/strongswan.service /lib/systemd/system/strongswan.service

systemctl enable strongswan
systemctl restart strongswan
