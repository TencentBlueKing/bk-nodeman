# -*- coding: utf-8 -*-
from django.contrib import admin

from requests_tracker.models import Config, Exclude, Filter, Record


class RecordAdmin(admin.ModelAdmin):
    list_display = ("id",
                    '__unicode__',
                    # 'api_uid',
                    'status_code',
                    'show_date_created',
                    # 'operator',
                    'duration',
                    'state',
                    "request_host",
                    )
    list_filter = ('date_created', 'method', 'api_uid', 'status_code', 'state')
    search_fields = ('request_message', 'operator', 'response_message')

    fieldsets = (
        (None, {
            'fields': ('uid',),
        }),
        ("Request", {
            'fields': ('operator', 'method', 'url', 'request_message',),
        }),
        ("Response", {
            'fields': ('status_code', 'response_message', "request_host"),
        }),
        ("Other Infamation", {
            'fields': ('api_uid', 'state', 'remark',),
        }),
        ("Important Datetimes", {
            'fields': ('date_created', 'duration',),
        }),
    )

    readonly_fields = (
        'uid', 'operator',
        'method', 'url',
        'status_code', "request_host",
        'api_uid', 'state', 'remark',
        'date_created', 'duration'
    )
    ordering = ["-date_created"]

    def show_date_created(self, obj):
        return obj.date_created.strftime("%Y-%m-%d %H:%M:%S")

    show_date_created.short_description = "Date created"


class BaseFilterAdmin(admin.ModelAdmin):
    list_display = (
        '__unicode__', 'is_active',
        'column', 'category', 'rule',
    )
    list_filter = ('is_active', 'column', 'category',)
    search_fields = ('name', 'rule',)

    fieldsets = (
        (None, {
            'fields': ('name', 'is_active',),
        }),
        ("Filtering Rules", {
            'fields': ('column', 'category', 'rule',),
        }),
        ("Important Datetimes", {
            'fields': ('date_created', 'last_modified',),
        }),
    )

    readonly_fields = ('date_created', 'last_modified',)


class FilterAdmin(BaseFilterAdmin):
    pass


class ExcludeAdmin(BaseFilterAdmin):
    pass


class ConfigAdmin(admin.ModelAdmin):
    list_display = ("__unicode__",)


admin.site.register(Record, RecordAdmin)
admin.site.register(Filter, FilterAdmin)
admin.site.register(Exclude, ExcludeAdmin)
admin.site.register(Config, ConfigAdmin)
