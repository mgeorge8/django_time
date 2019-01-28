from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from timepiece.manager.models import (
    Project, Profile)

from import_export import resources

#needed for import/export to work
class ProjectResource(resources.ModelResource):

    class Meta:
        model = Project
        fields = ('id', 'name', 'inactive')

from import_export.admin import ImportExportModelAdmin
        
class ProjectAdmin(ImportExportModelAdmin):
    resource_class = ProjectResource



class UserProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'employee'
    

class UserProfileAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.register(Project, ProjectAdmin)
admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)
