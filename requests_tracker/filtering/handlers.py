"""
requests_tracker.filtering.handlers
===================================
"""
from django.core.cache import cache

from requests_tracker.models import Filter, Exclude
from requests_tracker.filtering import FILTER_CACHE_KEY, EXCLUDE_CACHE_KEY


def clear_cache(sender, *args, **kwargs):
    try:
        if sender == Filter:
            cache.delete(FILTER_CACHE_KEY)
        elif sender == Exclude:
            cache.delete(EXCLUDE_CACHE_KEY)
    except Exception:
        pass
