# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from libs.logger import log_notice
from libs.monitoring import UpdateMonitor, initial_prompt

initial_prompt()
update_monitor = UpdateMonitor()
log_notice('Service started')
update_monitor.waitForAbort()
log_notice('Service stopped')
