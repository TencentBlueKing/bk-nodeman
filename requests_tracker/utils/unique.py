"""
requests_tracker.utils.unique
=============================
"""
import uuid


def uniqid():
    return uuid.uuid3(
        uuid.uuid1(),
        uuid.uuid4().hex
    ).hex
