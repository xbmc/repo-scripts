from __future__ import absolute_import, division, print_function

from trakt.core.errors import log_request_error
from trakt.core.exceptions import ServerError, ClientError, RequestFailedError
from trakt.core.helpers import try_convert

from six.moves.urllib.parse import urlsplit, urlunsplit, parse_qsl
import logging

log = logging.getLogger(__name__)


class PaginationIterator(object):
    def __init__(self, client, request, exceptions=False):
        self.client = client
        self.request = request
        self.exceptions = exceptions

        self.per_page = None
        self.total_items = None
        self.total_pages = None

        self._mapper = None

        # Parse request url
        scheme, netloc, path, query = urlsplit(self.request.url)[:4]

        self.url = urlunsplit([scheme, netloc, path, '', ''])
        self.query = dict(parse_qsl(query))

        # Resolve pagination details
        self.resolve()

    def get(self, page):
        request = self.request.copy()

        # Build query parameters
        query = self.query.copy()
        query['page'] = page
        query['limit'] = self.per_page

        # Construct request
        request.prepare_url(self.url, query)

        # Send request
        response = self._send(request)

        if not response:
            return None

        # Parse response, return data
        content_type = response.headers.get('content-type')

        if content_type and content_type.startswith('application/json'):
            # Try parse json response
            try:
                items = response.json()
            except Exception as e:
                log.warning('Unable to parse page: %s', e)
                return None
        else:
            log.warning('Received a page with an invalid content type: %r', content_type)
            return None

        if self._mapper:
            return self._mapper(items)

        return items

    def resolve(self):
        request = self.request.copy()
        request.prepare_method('HEAD')

        # Send request
        if not self._send(request):
            log.warning('Unable to resolve pagination state')

            # Reset state
            self.per_page = None
            self.total_items = None
            self.total_pages = None

    def with_mapper(self, mapper):
        if self._mapper:
            raise ValueError('Iterator has already been bound to a mapper')

        # Update mapper
        self._mapper = mapper

        return self

    def _send(self, request):
        response = self.client.http.send(request)

        if response is None:
            if self.exceptions:
                raise RequestFailedError('No response available')

            log.warning('Request failed (no response returned)')
            return None

        if response.status_code < 200 or response.status_code >= 300:
            log_request_error(log, response)

            # Raise an exception (if enabled)
            if self.exceptions:
                if response.status_code >= 500:
                    raise ServerError(response)
                else:
                    raise ClientError(response)

            return None

        # Update pagination state
        self.per_page = try_convert(response.headers.get('x-pagination-limit'), int)
        self.total_items = try_convert(response.headers.get('x-pagination-item-count'), int)
        self.total_pages = try_convert(response.headers.get('x-pagination-page-count'), int)

        return response

    def __iter__(self):
        if self.total_pages is None:
            if self.exceptions:
                raise ValueError("Pagination state hasn't been resolved")

            log.warning("Pagination state hasn't been resolved")
            return

        # Retrieve current page number
        current = int(self.query.get('page', 1))

        # Fetch pages
        while current <= self.total_pages:
            items = self.get(current)

            if not items:
                log.warning('Unable to retrieve page #%d, pagination iterator cancelled', current)
                break

            for item in items:
                yield item

            current += 1
