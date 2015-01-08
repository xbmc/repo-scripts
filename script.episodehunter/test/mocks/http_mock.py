from mock_base_class import MockBaseClass


class HttpMock(MockBaseClass, object):

    return_value = {}

    def __init__(self, base_url):
        super(HttpMock, self).__init__()
        self.__base_url = base_url

    def make_request(self, api_endpoint, data=None):
        self._increase_called('make_request', (api_endpoint, data))
        return self.return_value
