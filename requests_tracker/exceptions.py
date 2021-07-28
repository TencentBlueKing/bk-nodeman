"""
requests_tracker.exceptions
===========================
"""


class ConcurrencyTransitionError(Exception):
    """ConcurrencyTransitionError"""
    pass


class StateTransitionError(Exception):
    """StateTransitionError"""
    pass
