from BaseHTTPServer import BaseHTTPRequestHandler
import json


# noinspection PyPep8Naming
class RemoteRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.onEventReceived(self.client_address[0], self.client_address[1], self.path)
        http_status = 200
        http_message = None
        message = None
        action = None

        if self.path == "/trigger/sync":
            action = "Sync"
            message = "Events Triggered"
            self.server.onSyncTriggered()
        else:
            http_status = 404
            http_message = "Trigger not implemented"

        result = {
            "message": message or http_message or "Ok",
        }
        if action:
            result["triggered"] = [action, ]

        self.send_response(http_status, message=http_message)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result))

    def do_HEAD(self):
        raise NotImplementedError()

    def do_POST(self):
        raise NotImplementedError()
