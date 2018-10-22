from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from timepiece.manager.models import (
    Project, Profile)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'inactive')
    search_fields = ('name', 'inactive') 


class UserProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'employee'
    

class UserProfileAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.register(Project, ProjectAdmin)
admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)
