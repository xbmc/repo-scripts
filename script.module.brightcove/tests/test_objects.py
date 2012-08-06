#from unittest import TestCase
#from brightcove.objects import Video, item_collection_factory

#TOKEN = 'cE97ArV7TzqBzkmeRVVhJ8O6GWME2iG_bRvjBTlNb4o.'

#class TestBrightcove(TestCase):
    #def test_init(self):
        #b = Brightcove(TOKEN)
        #self.assertEqual(b.token, TOKEN)

#class TestVideoApis(TestCase):
    #def setUp(self):
        #self.b = Brightcove(TOKEN)

    #def test_find_video_by_id(self):
        #video_id = 1809586456
        #v = self.b.find_video_by_id(video_id=video_id)
        #self.assertEqual(video_id, v.id)
        ##self.assertIsInstance(v, Video)

    #def test_find_related_videos_missing_arg(self):
        #self.assertRaises(AssertionError, self.b.find_related_videos)

    #def test_find_related_videos(self):
        #video_id = 1809586456
        #v = self.b.find_related_videos(video_id=video_id)
        

#class TestItemCollection(TestCase):
#    def test_item_collection_iter(self):
#        cls = item_collection_factory(str)
#        ic = cls(['foo', 'bar'])

#        for item in ic.items:
#            print item
#        print
#        print ic
#        print dir(ic)
#        for item in ic:
#            print item
#        assert False


