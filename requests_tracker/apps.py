"""
requests_tracker.apps
=====================
"""
from django.apps import AppConfig
from django.conf import settings


class RequestsTrackerConfig(AppConfig):
    name = 'requests_tracker'
    label = name
    verbose_name = "RequestsTracker"

    def ready(self):
        if getattr(settings, "NEED_TRACK_REQUEST", False):
            from requests_tracker import signals
            from requests_tracker.signals import handlers

            signals.pre_send.connect(
                handlers.pre_send_handler,
                dispatch_uid='requests_tracker.apps.ready.pre_send'
            )
            signals.response.connect(
                handlers.response_handler,
                dispatch_uid='requests_tracker.apps.ready.response'
            )
            signals.request_failed.connect(
                handlers.request_failed_handler,
                dispatch_uid='requests_tracker.apps.ready.request_failed'
            )

            from django.db.models import signals
            from requests_tracker.filtering import handlers

            signals.post_save.connect(
                handlers.clear_cache,
                dispatch_uid='requests_tracker.apps.ready.post_save'
            )
            signals.post_delete.connect(
                handlers.clear_cache,
                dispatch_uid='requests_tracker.apps.ready.post_delete'
            )

            from requests_tracker import monkey
            monkey.patch_all()
