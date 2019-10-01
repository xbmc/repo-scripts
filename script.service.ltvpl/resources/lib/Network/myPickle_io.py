#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import pickle
from resources.lib.Utilities.DebugPrint import DbgPrint

__Version__ = "1.0.1"

class myPickle_io(object):
    def __init__(self):
        pass

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def ExportPKL(self,fp):
        data=self.Data.copy()
        # DbgPrint("list:{}".format(data))
        data = pickle.dumps(data)
        fp.write(data.decode())
    

    def ImportPKL(self,fp):
        try:
            data = pickle.load(fp)
            self.Data = data.encode('utf-8')
        except:
            fp.seek(0,0)
            bdata = fp.read()
            data=pickle.loads(bdata.encode())
            self.Data=data
