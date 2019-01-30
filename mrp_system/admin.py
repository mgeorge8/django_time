from django.contrib import admin
from mrp_system.models import (Part, Location, LocationRelationship,
Vendor, ManufacturerRelationship, Type, Field)
from import_export import resources
from import_export.admin import ImportExportModelAdmin

"""these were made to allow models to be imported via excel or csv files but
they haven't been used"""
class PartResource(resources.ModelResource):
    class Meta:
        model = Part
        exclude = ('manufacturer','location')

class PartAdmin(ImportExportModelAdmin):
    resource_class = PartResource

class VendorResource(resources.ModelResource):
    class Meta:
        model = Vendor    

class VendorAdmin(ImportExportModelAdmin):
    resource_class = VendorResource

class ManufacturerRelationshipResource(resources.ModelResource):
    class Meta:
        model = ManufacturerRelationship    

class ManufacturerRelationshipAdmin(ImportExportModelAdmin):
    resource_class = ManufacturerRelationshipResource

class LocationResource(resources.ModelResource):
    class Meta:
        model = Location    

class LocationAdmin(ImportExportModelAdmin):
    resource_class = LocationResource

class LocationRelationshipResource(resources.ModelResource):
    class Meta:
        model = LocationRelationship    

class LocationRelationshipAdmin(ImportExportModelAdmin):
    resource_class = LocationRelationshipResource

class TypeResource(resources.ModelResource):
    class Meta:
        model = Type    

class TypeAdmin(ImportExportModelAdmin):
    resource_class = TypeResource

class FieldResource(resources.ModelResource):
    class Meta:
        model = Field    

class FieldAdmin(ImportExportModelAdmin):
    resource_class = FieldResource

    
admin.site.register(Part, PartAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(ManufacturerRelationship, ManufacturerRelationshipAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(LocationRelationship, LocationRelationshipAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(Field, FieldAdmin)
