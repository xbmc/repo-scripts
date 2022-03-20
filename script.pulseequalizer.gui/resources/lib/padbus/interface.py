#	This file is part of PulseEqualizerGui for Kodi.
#	
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#
#
INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties"
INTERFACE_INTROSPECTABLE = "org.freedesktop.DBus.Introspectable"

MANAGER_P='/org/pulseaudio/equalizing1'
MANAGER_I='org.PulseAudio.Ext.Equalizing1.Manager'
EQUALIZER_I='org.PulseAudio.Ext.Equalizing1.Equalizer'
DEVICE_I='org.PulseAudio.Core1.Device'

CORE_P ='/org/pulseaudio/core1'
CORE_I='org.PulseAudio.Core1'

STREAM_I = 'org.PulseAudio.Core1.Stream'
MODULE_I = 'org.PulseAudio.Core1.Module'
PORT_I = 'org.PulseAudio.Core1.DevicePort'
CARD_I = 'org.PulseAudio.Core1.Card'
CARDPROFILE_I = 'org.PulseAudio.Core1.CardProfile'
CLIENT_I = 'org.PulseAudio.Core1.Client'
