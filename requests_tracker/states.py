"""
requests_tracker.states
=======================
"""
from requests_tracker.utils.collections import ConstantDict

CREATED = 'CREATED'
IN_PROGRESS = 'IN_PROGRESS'
SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'

ARCHIVED_STATES = frozenset([SUCCESS, FAILURE])

ALL_STATES = frozenset([CREATED, IN_PROGRESS, SUCCESS, FAILURE])

_TRANSITION = ConstantDict({
    CREATED: frozenset([IN_PROGRESS]),
    IN_PROGRESS: frozenset([SUCCESS, FAILURE]),
    SUCCESS: frozenset([]),
    FAILURE: frozenset([]),
})


def can_transit(from_state, to_state):
    """Test if :param:`from_state` can transit to :param:`to_state`::

        >>> can_transit(CREATED, IN_PROGRESS)
        True

        >>> can_transit(SUCCESS, FAILURE)
        False
    """
    if from_state in _TRANSITION:
        if to_state in _TRANSITION[from_state]:
            return True
    return False
