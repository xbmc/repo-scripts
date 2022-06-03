# This is a basic solution for getting the access token from an OAuth 2 server.
#
# When you want to grant a piece of software access to an API, you often need to
# open a web browser, go to that API, authorise the access, and you are then
# redirected to a new URL with the appropriate access token passed in the
# request.
#
# This works fine for web apps, but command-line ones won't normally be
# exposing a URL to which OAuth can redirect. So we run a simple server that
# can be specified as the redirection address, and then make the token available
# when it comes through.
#
# OAuth 2 does require HTTPS, so we have to use a certificate.
# You can generate one and a key in the current directory with:
#
#    openssl req -x509 -nodes -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365
#
# We will look for 'key.pem' and 'cert.pem' when serving.  This is a self-signed key
# so you'll probably need to tell your browser that it really is OK to go to this URL.
#
# You should specify 'https://localhost:8584' as the redirection address to the API.


from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl

LOCAL_SERVER_PORT = 8584


class CollectorException(Exception):
    pass


class TokenReceivingServer(HTTPServer):
    """
    A simple HTTP server that listens on the specified port
    and stores the URL of the last request it received.
    """
    def __init__(self, port):
        self.received_request = None
        self.port = port
        print("Starting a small HTTP server to receive the callback")
        super().__init__(('', port), TokenHandler)

    def save_request(self, request: str):
        self.received_request = request

    def last_request(self) -> str:
        return self.received_request


class TokenHandler(BaseHTTPRequestHandler):
    """
    A little HTTP request handler which expects a token
    and stores it in the server.
    """
    def do_GET(self):
        self.server.save_request(self.path)
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(
            "Thank you.  Authentication token received. You can close this window.".encode()
        )


class TokenCollector():

    def __init__(self):
        self.http_server = TokenReceivingServer(LOCAL_SERVER_PORT)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        self.http_server.socket = context.wrap_socket(
            self.http_server.socket,
            server_side=True
        )

    def get_single_request(self):
        # Could make this wait until we have something that looks like a token
        print(f"Waiting for the callback on port {LOCAL_SERVER_PORT}...")
        while True:
            self.http_server.handle_request()
            req = self.http_server.last_request()
            if req is not None:
                break
        return f"https://localhost:{LOCAL_SERVER_PORT}{req}"

