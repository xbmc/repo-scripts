#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from threading import Thread

from clouddrive.common.ui.utils import KodiUtils


class ServiceUtil(object):
    @staticmethod
    def run(services):
        if type(services) != list:
            services = [services]
        for service in services:
            thread = Thread(target=service.start, name='service-%s' % service.name)
            thread.daemon = True
            thread.start()
        monitor = KodiUtils.get_system_monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
        for service in services:
            service.stop()

   

