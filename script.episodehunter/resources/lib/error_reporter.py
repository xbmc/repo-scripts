import json
from resources.lib.connection.http import Http
from resources.lib import helper
from resources.lib.gui import dialog

def extract_call_stack():
    import traceback
    return traceback.format_exc()


def print_exception_information():
    helper.debug(extract_call_stack())


def report_error(*msg):
    error_stack = extract_call_stack()
    helper.debug(error_stack)
    dialog.create_ok(helper.language(32018), *msg)
    send_report_to_eh(error_stack)


def send_report_to_eh(error_stack):
    http = Http()

    if helper.send_debug_reports():
        result = True
    else:
        result = dialog.create_yes_no("Do you want to send a bug report to episodehunter.tv?")

    if result:
        try:
            http.make_request('/v2/error_report', json.dumps(dict(error=error_stack)))
        except Exception:
            helper.debug('Faild to send error report')
