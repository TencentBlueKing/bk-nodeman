"""
requests_tracker.filtering.columns
==================================
"""

API_UID = 0
METHOD = 10
SCHEME = 100
NETLOC = 101
PATH = 102
QUERY = 103
FRAGMENT = 104

ALL_COLUMNS = [API_UID, METHOD,
               SCHEME, NETLOC, PATH, QUERY, FRAGMENT]

COLUMN_CHOICES = (
    (API_UID, 'api_uid'),
    (METHOD, 'method'),
    (SCHEME, 'url:scheme'),
    (NETLOC, 'url:netloc'),
    (PATH, 'url:path'),
    (QUERY, 'url:query'),
    (FRAGMENT, 'url:fragment'),
)


def get_column_name(column):
    return dict(COLUMN_CHOICES)[column]
