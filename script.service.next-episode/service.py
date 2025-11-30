# (c) Roman Miroshnychenko, 2023
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging

from libs.exception_logger import catch_exception
from libs.logger import initialize_logging
from libs.monitoring import UpdateMonitor, initial_prompt

initialize_logging()
with catch_exception(logging.error):
    initial_prompt()
    update_monitor = UpdateMonitor()
    logging.debug('Service started')
    update_monitor.waitForAbort()
    logging.debug('Service stopped')
