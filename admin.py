"""admin settings for nps app"""
import datetime
from django.contrib import admin
from django.utils import timezone as dtz
from .models import *


class DataMapInline(admin.TabularInline):
    model = DataMap
    extra = 0


class ForceAPIAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('user_id',)
            }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('password','user_token','consumer_key',
                'consumer_secret','request_token_url',
                'access_token_url')
            }),
        )
    inlines = [DataMapInline]


class MapObjectInline(admin.TabularInline):
    model = MapObject
    extra = 0


class MapSchedInline(admin.TabularInline):
    model = MapSched
    extra = 0


def refresh_map(modeladmin, request, queryset):
    for obj in queryset:
        obj.load_sf_data()
refresh_map.short_description = 'Realtime Refresh from SalesForce'

def refresh_map_bkgd(modeladmin, request, queryset):
    for obj in queryset:
        ts = obj.mapsched_set.create(
            frequency=10,
            freq_unit='DY')
        ts.end = ts.start + datetime.timedelta(days=1)
        ts.save()
refresh_map_bkgd.short_description = 'Refresh from SalesForce'

class DataMapAdmin(admin.ModelAdmin):
    list_display = ('name', 'map_active', 'last_refresh')
    inlines = [MapObjectInline, MapSchedInline]
    actions = [refresh_map_bkgd, refresh_map]


class MapFieldInline(admin.TabularInline):
    model = MapField
    fk_name = 'map_object'
    extra = 0


class MapObjectAdmin(admin.ModelAdmin):
    inlines = [MapFieldInline]


class MapFilterInline(admin.TabularInline):
    model = MapFilter
    extra = 0


class MapFieldAdmin(admin.ModelAdmin):
    inlines = [MapFilterInline]


admin.site.register(ForceAPI, ForceAPIAdmin)
admin.site.register(DataMap, DataMapAdmin)
admin.site.register(MapObject, MapObjectAdmin)
admin.site.register(MapField, MapFieldAdmin)
