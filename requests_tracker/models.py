"""
requests_tracker.models
=======================
"""
from django.db import models, transaction
from django.utils.timezone import now

from requests_tracker import http_methods
from requests_tracker import states
from requests_tracker.exceptions import (
    ConcurrencyTransitionError, StateTransitionError
)
from requests_tracker.filtering import categories
from requests_tracker.filtering import columns


class Record(models.Model):
    # tracking record info
    uid = models.UUIDField(unique=True)
    api_uid = models.CharField(
        max_length=64,
        blank=True,
        default=''
    )
    state = models.CharField(
        max_length=16,
        choices=zip(states.ALL_STATES, states.ALL_STATES),
        default=states.CREATED
    )
    remark = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )
    # request info
    method = models.CharField(
        max_length=8,
        choices=zip(http_methods.ALL_METHODS, http_methods.ALL_METHODS),
        default=http_methods.GET
    )
    url = models.URLField(max_length=255)
    request_message = models.TextField(blank=True)
    operator = models.CharField(max_length=255)
    request_host = models.CharField(max_length=128)

    # response info
    status_code = models.PositiveSmallIntegerField(default=0)
    response_message = models.TextField(blank=True)

    # important datetimes
    date_created = models.DateTimeField(default=now)
    duration = models.DurationField(blank=True, null=True)

    def __unicode__(self):
        return u"%s %s" % (self.method, self.url)

    @transaction.atomic
    def transit(self, to_state, **kwargs):
        if states.can_transit(self.state, to_state):
            kwargs.update({'state': to_state})

            rows = Record.objects.filter(pk=self.pk, state=self.state) \
                .update(**kwargs)

            if rows:
                for k, v in kwargs.items():
                    setattr(self, k, v)
            else:
                msg = "transit from %r to %r conflicted." \
                      % (self.state, to_state)
                raise ConcurrencyTransitionError(msg)
        else:
            msg = "can not transit from %r to %r" % (self.state, to_state)
            raise StateTransitionError(msg)

    @transaction.atomic
    def update(self, **kwargs):
        Record.objects.filter(pk=self.pk).update(**kwargs)
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    class Meta:
        db_table = "Records"


class AbstractFilter(models.Model):
    name = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=False)

    # filter rules
    column = models.PositiveSmallIntegerField(
        choices=columns.COLUMN_CHOICES,
    )
    category = models.PositiveSmallIntegerField(
        choices=categories.CATEGORY_CHOICES,
        default=categories.EQUAL,
    )
    rule = models.CharField(max_length=1024)

    # important dates
    date_created = models.DateTimeField(default=now)
    last_modified = models.DateTimeField(auto_now=True, blank=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"[#%s] %s" % (self.pk, self.name)


class Filter(AbstractFilter):
    pass

    class Meta:
        db_table = "Filters"


class Exclude(AbstractFilter):
    pass

    class Meta:
        db_table = "Excludes"


class Config(models.Model):
    key = models.CharField('键', max_length=255, db_index=True, primary_key=True)
    value = models.BooleanField("值", default=False)

    def __unicode__(self):
        return "{}: {}".format(self.key, self.value)
