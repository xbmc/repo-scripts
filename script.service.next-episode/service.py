# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from __future__ import unicode_literals

from libs.exception_logger import log_exception
from libs.logger import log_info
from libs.monitoring import UpdateMonitor, initial_prompt

with log_exception():
    initial_prompt()
    update_monitor = UpdateMonitor()
    log_info('Service started')
    update_monitor.waitForAbort()
    log_info('Service stopped')
