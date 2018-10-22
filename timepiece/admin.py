from django.contrib import admin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class PermissionAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'codename', 'name']
    list_filter = ['content_type__app_label']

admin.site.register(Permission, PermissionAdmin)
