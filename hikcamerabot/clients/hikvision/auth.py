from typing import Generator

import httpx


class DigestAuthCached(httpx.DigestAuth):
    """Hack from https://github.com/encode/httpx/issues/1467."""

    __challenge = None

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if self.__challenge:
            request.headers['Authorization'] = self._build_auth_header(
                request, self.__challenge
            )

        response = yield request

        if response.status_code != 401 or 'www-authenticate' not in response.headers:
            # If the response is not a 401 then we don't
            # need to build an authenticated request.
            return

        for auth_header in response.headers.get_list('www-authenticate'):
            if auth_header.lower().startswith('digest '):
                break
        else:
            # If the response does not include a 'WWW-Authenticate: Digest ...'
            # header, then we don't need to build an authenticated request.
            return

        self.__challenge = self._parse_challenge(request, response, auth_header)
        request.headers['Authorization'] = self._build_auth_header(
            request, self.__challenge
        )
        yield request
