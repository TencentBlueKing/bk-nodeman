"""
requests_tracker.requests
=========================
"""

from __future__ import absolute_import

import json as JSON

from django.core.cache import cache
from django.utils.timezone import now
from requests.models import Request
from requests.packages.urllib3.connectionpool import HTTPConnectionPool
from requests.sessions import Session as _Session

from requests_tracker.models import Config
from requests_tracker.signals import pre_send, request_failed, response
from requests_tracker.utils.unique import uniqid

__implements__ = ["Session"]


def _make_request(self, conn, method, url, **kwargs):
    resp = self._old_make_request(conn, method, url, **kwargs)
    sock = getattr(conn, "sock", False)
    if sock:
        try:
            setattr(resp, "peer", sock.getpeername())
        except AttributeError:
            setattr(resp, "peer", sock.socket.getpeername())
    else:
        setattr(resp, "peer", None)
    return resp


HTTPConnectionPool._old_make_request = HTTPConnectionPool._make_request
HTTPConnectionPool._make_request = _make_request


class Session(_Session):
    def request(
        self,
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
        api_uid=None,
        operator=None,
    ):
        """
        patched requests.session.Session
        """
        # Create the Request.
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)

        proxies = proxies or {}

        settings = self.merge_environment_settings(prep.url, proxies, stream, verify, cert)

        # Send the request.
        send_kwargs = {
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        send_kwargs.update(settings)

        # Send pre_send signal
        uid = uniqid()
        if not operator:
            try:
                operator = JSON.loads(data).get("operator")
            except Exception:
                pass

        try:
            is_track = cache.get("is_track")
            if is_track is None:
                value = Config.objects.get(key="is_track").value
                is_track = value
                cache.set("is_track", value)
        except Exception:
            is_track = False

        if is_track:
            pre_send.send(sender=self.request, uid=uid, prep=prep, api_uid=api_uid, operator=operator)

        # Send the request.
        try:
            before_time = now()
            resp = self.send(prep, **send_kwargs)
            duration = now() - before_time
        except Exception as e:
            duration = now() - before_time
            request_failed.send(sender=self.request, uid=uid, exception=e, duration=duration)
        else:
            if is_track:
                response.send(sender=self.request, uid=uid, resp=resp, duration=duration)

        return resp
