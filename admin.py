"""admin settings for nps app"""
from django.contrib import admin
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


class DataMapAdmin(admin.ModelAdmin):
    inlines = [MapObjectInline]


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
