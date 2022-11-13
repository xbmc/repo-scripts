import os
import sys
import tempfile
import zipfile
import unittest
#from lib import zimuku_agent as zmkagnt


class Logger:
    def log(self, module, msg, level=0):
        lvls = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL')
        print('[%s]%s: %s' % (lvls[level], module, msg))


class Unpacker:
    def __init__(self, folder):
        self.folder = folder

    def unpack(self, path):
        zip_ref = zipfile.ZipFile(path, 'r')
        file_list = zip_ref.namelist()
        parent = ''
        if file_list[0][-1:] == '/':
            parent = file_list.pop(0)
            file_list = [x.replace(parent, '') for x in file_list]

        zip_ref.extractall(self.folder)

        return os.path.join(self.folder, parent), file_list


class TestZimukuAgent(unittest.TestCase):
    def setUp(self):
        lib_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.realpath(os.path.realpath(__file__))),
                os.pardir, 'resources'))
        sys.path.insert(0, lib_dir)

        global zmkagnt
        from lib import zimuku_agent as zmkagnt

        global tmp_folder
        tmp_folder = tempfile.TemporaryDirectory().name
        os.mkdir(tmp_folder)

        return super().setUp()

    def get_agent(self, settings):
        return zmkagnt.Zimuku_Agent(
            'http://zimuku.org', tmp_folder, Logger(),
            Unpacker(tmp_folder),
            settings)

    def test_search(self):
        # 测试搜索功能
        agent = self.get_agent({'subtype': 'srt', 'sublang': 'dualchs'})

        items = {
            'temp': False, 'rar': False, 'mansearch': False, 'year': '2021', 'season': '4',
            'episode': '17', 'tvshow': '小谢尔顿', 'title': '由一个黑洞引发的联想',
            'file_original_path':
            'Young.Sheldon.S04E17.720p.HEVC.x265-MeGusta.mkv',
            '3let_language': ['eng']}
        result = agent.search('小谢尔顿', items)
        self.assertNotEqual(len(result), 0)

    def test_search2(self):
        # 测试搜索功能
        agent = self.get_agent({'subtype': 'srt', 'sublang': 'dualchs'})

        items = {
            'temp': False, 'rar': False, 'mansearch': False, 'year': '2010', 'season': '6',
            'episode': '2', 'tvshow': '唐顿庄园', 'title': 'Episode 2',
            'file_original_path':
            'F:\\Downton.Abbey.2010.S06E02.1080p.BluRay.DD.2.0.x265.10bit-monster6688.mkv',
            '3let_language': ['', 'eng']}
        result = agent.search('唐顿庄园', items)
        self.assertNotEqual(len(result), 0)

    def test_deep_search(self):
        # 搜索不在第一页的字幕
        agent = self.get_agent({'subtype': 'srt', 'sublang': 'dualchs'})

        items = {
            'temp': False, 'rar': False, 'mansearch': False, 'year': '2021', 'season': '12',
            'episode': '3', 'tvshow': '生活大爆炸', 'title': '',
            'file_original_path': 'v.mkv',
            '3let_language': ['eng']}
        result = agent.search('生活大爆炸', items)
        self.assertEqual(len(result), 3)

    def test_search_movie(self):
        agent = self.get_agent({'subtype': 'srt', 'sublang': 'dualchs'})

        items = {
            'temp': False, 'rar': False, 'mansearch': False, 'year': '2018', 'season': '',
            'episode': '', 'tvshow': '', 'title': 'Free Solo',
            'file_original_path':
            'Free.Solo.2018.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTG.mkv',
            '3let_language': ['', 'eng']}
        result = agent.search('Free Solo', items)
        self.assertEqual(len(result), 8)

    def test_download(self):
        # 测试下载功能
        agent = self.get_agent({'subtype': 'none', 'sublang': 'none'})

        l1, l2 = agent.download('http://zimuku.org/detail/154168.html')
        self.assertIsNotNone(l1)
        self.assertIsNotNone(l2)
        self.assertEqual(len(l1), 9)

    def test_filter_sub(self):
        # 测试基于插件偏好设置的字幕过滤功能
        l1 = ['Mare.of.Easttown.S01E03-TEPES.简体&英文.ass',
              'Mare.of.Easttown.S01E03-TEPES.简体&英文.srt',
              'Mare.of.Easttown.S01E03-TEPES.简体.ass',
              'Mare.of.Easttown.S01E03-TEPES.简体.srt',
              'Mare.of.Easttown.S01E03-TEPES.繁体&英文.ass',
              'Mare.of.Easttown.S01E03-TEPES.繁体&英文.srt',
              'Mare.of.Easttown.S01E03-TEPES.繁体.ass',
              'Mare.of.Easttown.S01E03-TEPES.繁体.srt',
              'Mare.of.Easttown.S01E03-TEPES.英文.srt']
        l2 = ['c:\\Mare.of.Easttown.S01E03-TEPES.简体&英文.ass',
              'c:\\Mare.of.Easttown.S01E03-TEPES.简体&英文.srt',
              'c:\\Mare.of.Easttown.S01E03-TEPES.简体.ass',
              'c:\\Mare.of.Easttown.S01E03-TEPES.简体.srt',
              'c:\\Mare.of.Easttown.S01E03-TEPES.繁体&英文.ass',
              'c:\\Mare.of.Easttown.S01E03-TEPES.繁体&英文.srt',
              'c:\\Mare.of.Easttown.S01E03-TEPES.繁体.ass',
              'c:\\Mare.of.Easttown.S01E03-TEPES.繁体.srt',
              'c:\\Mare.of.Easttown.S01E03-TEPES.英文.srt']

        agent = self.get_agent({'subtype': 'srt', 'sublang': 'none'})

        self.assertEqual(len(agent.get_preferred_subs(l1, l2)[0]), 5)

        agent.set_setting({'subtype': 'none', 'sublang': 'cht'})
        self.assertEqual(len(agent.get_preferred_subs(l1, l2)[0]), 2)

        agent.set_setting({'subtype': 'ass', 'sublang': 'dualchs'})
        self.assertEqual(len(agent.get_preferred_subs(l1, l2)[0]), 1)

    def test_garbled_archive(self):
        # 测试文件名乱码的压缩包是否能正确处理
        agent = self.get_agent({'subtype': 'none', 'sublang': 'none'})
        url = 'http://zimuku.org/detail/154168.html'    # 乱码字幕
        l1, l2 = agent.download(url)
        self.assertIn('young.sheldon.s04e18.720p.hdtv.x264-syncopy.英文.srt', l1)
        url = 'http://zimuku.org/detail/155101.html'    # 正常字幕
        l1, l2 = agent.download(url)
        self.assertIn('black.monday.s03e01.720p.web.h264-ggez.繁体.srt', l1)

    def test_sub_rating(self):
        agent = self.get_agent({'subtype': 'none', 'sublang': 'none'})
        items = {
            'temp': False, 'rar': False, 'mansearch': False, 'year': '', 'season': '2',
            'episode': '4', 'tvshow': '9号秘事', 'title': '',
            'file_original_path':
            'tv.mkv', '3let_language': ['eng']}
        result = agent.search('9号秘事', items)
        self.assertEqual(len(result), 1)
        sub = result[0]
        self.assertEqual(sub['rating'], '4')


if __name__ == '__main__':
    unittest.main()
