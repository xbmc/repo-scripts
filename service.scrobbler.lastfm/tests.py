import unittest
import helpers

class TestLastFM(unittest.TestCase):
    """A set of unit tests for the last.fm scrobbler plugin. To execute, run
    
    $ python -m unittest tests
    """

    def testRemoteURL(self):
        assert helpers.is_local("http://www.google.com") == False
        assert helpers.is_local("rtmp://a.rtmp.youtube.com/videolive?ns=yt-live&id=123456&itag=35&signature=blahblahblah/yt-live.123456.35") == False

    def testLocalFileURLs(self):
        assert helpers.is_local("/local/path") == True
        assert helpers.is_local("nonesuch") == True
        assert helpers.is_local("file:///local/path") == True
        assert helpers.is_local("smb://server/share/artist/album/song.mp3") == True
        assert helpers.is_local("musicdb://artists/22/11/123.mp3?albumartistsonly=false&albumid=11&artistid=22") == True
        assert helpers.is_local("musicdb://songs/123.mp3") == True

    def testLocalIPv4URLs(self):
        assert helpers.is_local("http://8.8.8.8/File.mp3") == False
        assert helpers.is_local("rtmp://8.8.8.8/File.mp3") == False

        assert helpers.is_local("http://127.0.4.5/File.mp3") == True
        assert helpers.is_local("http://192.168.0.10/File.mp3") == True
        assert helpers.is_local("http://10.0.2.8/File.mp3") == True
        assert helpers.is_local("http://172.16.6.89/File.mp3") == True
        assert helpers.is_local("http://172.25.6.89/File.mp3") == True
        
        assert helpers.is_local("http://192.168.0.7:8200/MediaItems/40.mp3") == True

        assert helpers.is_local("rtmp://127.0.4.5/File.mp3") == True
        assert helpers.is_local("rtmp://192.168.0.10/File.mp3") == True
        assert helpers.is_local("rtmp://10.0.2.8/File.mp3") == True
        assert helpers.is_local("rtmp://172.16.6.89/File.mp3") == True
        assert helpers.is_local("rtmp://172.25.6.89/File.mp3") == True

    def testLocalIPv6URLs(self):
        assert helpers.is_local("http://fe80::ffff:ffff:ffff:ffff/File.mp3") == True
        assert helpers.is_local("rtmp://fe80::ffff:ffff:ffff:ffff/File.mp3") == True

        assert helpers.is_local("http://fc00::ffff:ffff:ffff:ffff/File.mp3") == True
        assert helpers.is_local("rtmp://fc00::ffff:ffff:ffff:ffff/File.mp3") == True
        
        assert helpers.is_local("http://2607:f8b0:4005:800::1006/File.mp3") == False
        assert helpers.is_local("rtmp://2607:f8b0:4005:800::1006/File.mp3") == False

if __name__ == '__main__':
    unittest.main()
