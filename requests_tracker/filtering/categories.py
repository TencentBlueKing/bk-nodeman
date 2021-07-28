"""
requests_tracker.filtering.categories
=====================================
"""

EQUAL = 0
BRE = 1
ERE = 2

ALL_CATEGORIES = [EQUAL, BRE, ERE]

CATEGORY_CHOICES = (
    (EQUAL, "equal"),
    (BRE, "basic-re"),
    (ERE, "extended-re"),
)
