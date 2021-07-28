"""
requests_tracker.monkey
=======================
"""
from __future__ import absolute_import

__all__ = [
    'patch_all',
    'patch_module',
]

targets = {
    'requests.sessions': None,
}


def patch_module(name, items=None):
    """
    The codes below comes from gevent.monkey.patch_module()
    """
    rt_module = __import__('requests_tracker.' + name)
    target_module = __import__(name)
    for i, submodule in enumerate(name.split('.')):
        rt_module = getattr(rt_module, submodule)
        if i:
            target_module = getattr(target_module, submodule)
    items = items or getattr(rt_module, '__implements__', None)
    if items is None:
        items = getattr(rt_module, '__implements__', None)
        if items is None:
            raise AttributeError('%r does not have __implements__' % rt_module)
    for attr in items:
        setattr(target_module, attr, getattr(rt_module, attr))
    return target_module


def patch_all():
    for module, items in targets.items():
        patch_module(module, items=items)
