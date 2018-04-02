# -*- coding: utf-8 -*-

from . import test_sub_common


class TestOomusicSubBookmark(test_sub_common.TestOomusicSubCommon):

    def test_00_getBookmarks(self):
        '''
        Test getBookmarks method
        '''
        self.env2.cr.release()
        res = self.url_open('/rest/getBookmarks.view' + self.cred).content.decode('utf-8')
        res_clean = ''.join(res.split('\n')[2:][:-2])
        self.assertEqual(res_clean, '  <bookmarks/>')
        self.cleanUp()

    def test_10_actionBookmark(self):
        '''
        Test actionBookmark method
        '''
        self.env2.cr.release()
        res = self.url_open('/rest/createBookmark.view' + self.cred).content.decode('utf-8')
        res_clean = ''.join(res.split('\n')[2:][:-2])
        self.assertEqual(res_clean, '')
        res = self.url_open('/rest/deleteBookmark.view' + self.cred).content.decode('utf-8')
        res_clean = ''.join(res.split('\n')[2:][:-2])
        self.assertEqual(res_clean, '')
        res = self.url_open('/rest/getPlayQueue.view' + self.cred).content.decode('utf-8')
        res_clean = ''.join(res.split('\n')[2:][:-2])
        self.assertEqual(res_clean, '')
        res = self.url_open('/rest/savePlayQueue.view' + self.cred).content.decode('utf-8')
        res_clean = ''.join(res.split('\n')[2:][:-2])
        self.assertEqual(res_clean, '')
        self.cleanUp()
