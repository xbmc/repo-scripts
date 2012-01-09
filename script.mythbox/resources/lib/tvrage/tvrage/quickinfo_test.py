#!#!/opt/local/bin/python

# Copyright (c) 2009, Christian Kreutzer
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import unittest
import quickinfo

from exceptions import ShowNotFound

class QuickInfoTest(unittest.TestCase):
    
    def test_showinfo(self):
        show = quickinfo.fetch('Doctor Who 2005')
        
        assert show['Show ID'] == '3332'
        assert show['Show Name'] == 'Doctor Who (2005)'
        assert show['Show URL'] == 'http://www.tvrage.com/DoctorWho_2005'
        assert show['Premiered'] == '2005'
        assert show['Started'] == 'Mar/26/2005'
        assert show['Ended'] == ''
        # Note: this test may break around X-mas 2010
        #assert show['Latest Episode'] == \
        #    ['05x13', 'The Big Bang (2)', 'Jun/26/2010']
        assert show['Country'] == 'United Kingdom'
        # hope the next one never breaks ;-)
        assert show['Status'] == 'Returning Series'
        assert show['Classification'] == 'Scripted'
        assert show['Genres'] == ['Action', 'Adventure', 'Sci-Fi']
        assert show['Network'] == 'BBC One (United Kingdom)'
        assert show['Airtime'] == 'Saturday at 06:00 pm' #this may break
        assert show['Runtime'] == '50'
        
    def test_epinfo(self):
        
        show_ep = quickinfo.fetch('Doctor Who 2005', ep='1x01')
        
        assert show_ep['Episode Info'] == ['01x01', 'Rose', '26/Mar/2005']
        assert show_ep['Episode URL'] == \
            'http://www.tvrage.com/DoctorWho_2005/episodes/52117'
        
    def test_non_existant_show_raises_proper_exception(self):
        try:
            quickinfo.fetch('yaddayadda')
        except Exception, e:
            assert isinstance(e, ShowNotFound)
            assert e.value == 'yaddayadda'

if __name__ == '__main__':
    unittest.main()
        