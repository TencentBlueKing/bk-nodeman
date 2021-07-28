"""
requests_tracker.filtering.filters
==================================
"""
import fnmatch
import logging
import re

from six.moves.urllib import parse

from django.core.cache import cache
from requests_tracker.filtering import (
    FILTER_CACHE_KEY, EXCLUDE_CACHE_KEY,
    FILTERS_CACHE_TIME,
    categories, columns
)
from requests_tracker.models import Filter, Exclude

FIELDS = ('column', 'category', 'rule')

logger = logging.getLogger(__name__)
urlsplit = parse.urlsplit


def _get_filters(use_cache=True):
    data = cache.get(FILTER_CACHE_KEY)

    if not (use_cache and data):
        data = Filter.objects.filter(is_active=True) \
                             .values_list(*FIELDS) \
                             .order_by('column')
        cache.set(FILTER_CACHE_KEY, data, FILTERS_CACHE_TIME)

    return data


def _get_excludes(use_cache=True):
    data = cache.get(EXCLUDE_CACHE_KEY)

    if not (use_cache and data):
        data = Exclude.objects.filter(is_active=True) \
                              .values_list(*FIELDS) \
                              .order_by('column')
        cache.set(EXCLUDE_CACHE_KEY, data, FILTERS_CACHE_TIME)

    return data


def _match(column, category, rule, prepared_request):
    column_name = columns.get_column_name(column)

    if column_name.startswith('url:'):
        column_name = column_name.split(':')[1]
        target = getattr(urlsplit(prepared_request.url), column_name)
    else:
        target = getattr(prepared_request, column_name)

    if category == categories.EQUAL:
        return target == rule
    if category == categories.BRE:
        try:
            return fnmatch.fnmatch(target, rule)
        except Exception as e:
            logger.error("invalid filtering rule of column %r: %r\n%s",
                         column_name, rule, e)
            return True
    if category == categories.ERE:
        try:
            return re.search(rule, target)
        except Exception as e:
            logger.error("invalid filtering rule of column %r: %r\n%s",
                         column_name, rule, e)
            return True


def _filter(prepared_request, use_cache=True):
    for column, category, rule in _get_filters(use_cache):
        if not _match(column, category, rule, prepared_request):
            return False
    return True


def _exclude(prepared_request, use_cache=True):
    for column, category, rule in _get_excludes(use_cache):
        if _match(column, category, rule, prepared_request):
            return False
    return True


def rt_filter(prepared_request, use_cache=True):
    return _exclude(prepared_request, use_cache) \
        and _filter(prepared_request, use_cache)
