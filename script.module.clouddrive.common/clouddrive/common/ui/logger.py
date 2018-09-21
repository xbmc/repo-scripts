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

class Logger:
    @staticmethod
    def debug(msg):
        from clouddrive.common.ui.utils import KodiUtils
        KodiUtils.log(msg, KodiUtils.LOGDEBUG)
    
    @staticmethod
    def notice(msg):
        from clouddrive.common.ui.utils import KodiUtils
        KodiUtils.log(msg, KodiUtils.LOGNOTICE)
    
    @staticmethod
    def warning(msg):
        from clouddrive.common.ui.utils import KodiUtils
        KodiUtils.log(msg, KodiUtils.LOGWARNING)
        
    @staticmethod
    def error(msg):
        from clouddrive.common.ui.utils import KodiUtils
        KodiUtils.log(msg, KodiUtils.LOGERROR)
