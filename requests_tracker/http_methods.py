"""
requests_tracker.http_methods
=============================
"""

GET = 'GET'
OPTIONS = 'OPTIONS'
HEAD = 'HEAD'
POST = 'POST'
PUT = 'PUT'
PATCH = 'PATCH'
DELETE = 'DELETE'

ALL_METHODS = frozenset((GET,
                         OPTIONS,
                         HEAD,
                         POST,
                         PUT,
                         PATCH,
                         DELETE))
