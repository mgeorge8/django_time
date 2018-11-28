from django.contrib import admin
from redirect.models import Redirect
from import_export import resources
from import_export.admin import ImportExportModelAdmin


class RedirectResource(resources.ModelResource):
    class Meta:
        model = Redirect
        fields = ('id', 'site', 'old_path', 'new_path')
        
class RedirectAdmin(ImportExportModelAdmin):
    list_display = ('old_path', 'new_path')
    list_filter = ('site',)
    search_fields = ('old_path', 'new_path')
    radio_fields = {'site': admin.VERTICAL}

admin.site.register(Redirect, RedirectAdmin)
