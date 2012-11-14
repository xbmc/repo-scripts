import os
import re
import sys
import urllib
import urllib2
import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = 'script.xbmc.debug.log'
Addon = xbmcaddon.Addon(id=ADDON_ID)
ADDON_TITLE = Addon.getAddonInfo('name')

DEBUG = False


class LogUploader(object):

    STR_DO_UPLOAD = 30000
    STR_UPLOADED_ID = 30001
    STR_UPLOADED_URL = 30002
    STR_NO_EMAIL_SET = 30003
    STR_EMAIL_SENT_TO = 30004
    STR_UPLOAD_LINK = 'http://xbmclogs.com/show.php?id=%s'

    def __init__(self):
        self.__log('started')
        self.first_run()
        self.get_settings()
        found_logs = self.__get_logs()
        uploaded_logs = []
        for logfile in found_logs:
            if self.ask_upload(logfile['title']):
                paste_id = self.upload_file(logfile['path'])
                if paste_id:
                    uploaded_logs.append({'paste_id': paste_id,
                                          'title': logfile['title']})
                    self.report_msg(paste_id)
        if uploaded_logs and self.email_address:
            self.report_mail(self.email_address, uploaded_logs)
            pass

    def get_settings(self):
        self.email_address = Addon.getSetting('email')
        self.__log('settings: len(email)=%d' % len(self.email_address))
        self.skip_oldlog = Addon.getSetting('skip_oldlog') == 'true'
        self.__log('settings: skip_oldlog=%s' % self.skip_oldlog)

    def first_run(self):
        if not Addon.getSetting('already_shown') == 'true':
            Addon.openSettings()
            Addon.setSetting('already_shown', 'true')

    def upload_file(self, filepath):
        url = 'http://xbmclogs.com/'
        self.__log('reading log...')
        file_content = open(filepath, 'r').read()
        self.__log('starting upload "%s"...' % filepath)
        post_dict = {'paste_data': file_content,
                     'api_submit': True,
                     'mode': 'xml'}
        if filepath.endswith('.log'):
            post_dict['paste_lang'] = 'xbmc'
        elif filepath.endswith('.xml'):
            post_dict['paste_lang'] = 'advancedsettings'
        post_data = urllib.urlencode(post_dict)
        req = urllib2.Request(url, post_data)
        response = urllib2.urlopen(req).read()
        self.__log('upload done.')
        r_id = re.compile('<id>([0-9]+)</id>', re.DOTALL)
        m_id = re.search(r_id, response)
        if m_id:
            paste_id = m_id.group(1)
            self.__log('paste_id=%s' % paste_id)
            return paste_id
        else:
            self.__log('upload failed with response: %s' % repr(response))

    def ask_upload(self, logfile):
        Dialog = xbmcgui.Dialog()
        msg1 = Addon.getLocalizedString(self.STR_DO_UPLOAD) % logfile
        if self.email_address:
            msg2 = (Addon.getLocalizedString(self.STR_EMAIL_SENT_TO)
                    % self.email_address)
        else:
            msg2 = Addon.getLocalizedString(self.STR_NO_EMAIL_SET)
        return Dialog.yesno(ADDON_TITLE, msg1, '', msg2)

    def report_msg(self, paste_id):
        url = self.STR_UPLOAD_LINK % paste_id
        Dialog = xbmcgui.Dialog()
        msg1 = Addon.getLocalizedString(self.STR_UPLOADED_ID) % paste_id
        msg2 = Addon.getLocalizedString(self.STR_UPLOADED_URL) % url
        return Dialog.ok(ADDON_TITLE, msg1, '', msg2)

    def report_mail(self, mail_address, uploaded_logs):
        url = 'http://xbmclogs.com/xbmc-addon.php'
        if not mail_address:
            raise Exception('No Email set!')
        post_dict = {'email': mail_address}
        for logfile in uploaded_logs:
            if logfile['title'] == 'xbmc.log':
                post_dict['xbmclog_id'] = logfile['paste_id']
            elif logfile['title'] == 'xbmc.old.log':
                post_dict['oldlog_id'] = logfile['paste_id']
            elif logfile['title'] == 'crash.log':
                post_dict['crashlog_id'] = logfile['paste_id']
        post_data = urllib.urlencode(post_dict)
        if DEBUG:
            print post_data
        req = urllib2.Request(url, post_data)
        response = urllib2.urlopen(req).read()
        if DEBUG:
            print response

    def __get_logs(self):
        if xbmc.getCondVisibility('system.platform.osx'):
            if xbmc.getCondVisibility('system.platform.atv2'):
                log_path = '/var/mobile/Library/Preferences'
            else:
                log_path = os.path.join(os.path.expanduser('~'), 'Library/Logs')
            crashlog_path = os.path.join(os.path.expanduser('~'),
                                         'Library/Logs/CrashReporter')
            crashfile_match = 'XBMC'
        elif xbmc.getCondVisibility('system.platform.ios'):
            log_path = '/var/mobile/Library/Preferences'
            crashlog_path = os.path.join(os.path.expanduser('~'),
                                         'Library/Logs/CrashReporter')
            crashfile_match = 'XBMC'
        elif xbmc.getCondVisibility('system.platform.windows'):
            log_path = xbmc.translatePath('special://home')
            crashlog_path = log_path
            crashfile_match = '.dmp'
        elif xbmc.getCondVisibility('system.platform.linux'):
            log_path = xbmc.translatePath('special://home/temp')
            crashlog_path = os.path.expanduser('~')
            crashfile_match = 'xbmc_crashlog'
        else:
            # we are on an unknown OS and need to fix that here
            raise Exception('UNHANDLED OS')
        # get fullpath for xbmc.log and xbmc.old.log
        log = os.path.join(log_path, 'xbmc.log')
        log_old = os.path.join(log_path, 'xbmc.old.log')
        # check for XBMC crashlogs
        log_crash = None
        if crashlog_path and crashfile_match:
            crashlog_files = [s for s in os.listdir(crashlog_path)
                              if os.path.isfile(os.path.join(crashlog_path, s))
                              and crashfile_match in s]
            if crashlog_files:
                # we have crashlogs, get fullpath from the last one by time
                crashlog_files = self.__sort_files_by_date(crashlog_path,
                                                           crashlog_files)
                log_crash = os.path.join(crashlog_path, crashlog_files[-1])
        found_logs = []
        if log and os.path.isfile(log):
            found_logs.append({'title': 'xbmc.log',
                               'path': log})
        if not self.skip_oldlog and log_old and os.path.isfile(log_old):
            found_logs.append({'title': 'xbmc.old.log',
                               'path': log_old})
        if log_crash and os.path.isfile(log_crash):
            found_logs.append({'title': 'crash.log',
                               'path': log_crash})
        return found_logs

    def __sort_files_by_date(self, path, files):
        files.sort(key=lambda f: os.path.getmtime(os.path.join(path, f)))
        return files

    def __log(self, msg):
        xbmc.log('%s: %s' % (ADDON_TITLE, msg))


if __name__ == '__main__':
    Uploader = LogUploader()
