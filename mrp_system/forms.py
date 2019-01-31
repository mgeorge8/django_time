from django import forms
from mrp_system.models import (Location, LocationRelationship,
Part, Vendor, ManufacturerRelationship, Field, Type, Product,
                               PartAmount, ProductAmount, ProductLocation,
                               MOProduct, ManufacturingOrder, PurchaseOrder,
                               PurchaseOrderParts)
from django.forms import ModelForm, BaseInlineFormSet
from django.forms.models import inlineformset_factory
from timepiece.forms import TimepieceSplitDateTimeField
from django.utils.safestring import mark_safe

class PartForm(ModelForm): 

        def __init__(self, type_id, *args, **kwargs):
            super(PartForm, self).__init__(*args, **kwargs)
            partType = Type.objects.get(id=type_id)
            """take label from Type/Field models and assign it to the
            correct field"""
            for field in partType.field.all():
                self.fields[field.fields].label = field.name
            field_options = []
            """generate a list of all possible fields"""
            for x in range(1,36):
                field_options.append('char' + str(x))
            for field in field_options:
                """if field hasn't been assigned to this type, don't include
                it in the form"""
                if field not in partType.field.values_list('fields', flat=True):
                    self.fields.pop(field)
            
        class Meta:
            model = Part
            exclude = ('manufacturer', 'location', 'partType')
            
class ManufacturerForm(ModelForm):
    manufacturer = forms.ModelChoiceField(queryset=Vendor.objects.filter(vendor_type='manufacturer').order_by('name'))
    class Meta:
        model = ManufacturerRelationship
        exclude = ('part',)

class CustomFormset(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                partNumber = form.cleaned_data['partNumber']
                #exclude self
                try:
                        mr = ManufacturerRelationship.objects.filter(part=self.instance, partNumber=partNumber)
                except ManufacturerRelationship.DoesNotExist:
                    pass
                
                if not mr:
                        #check if another part with same number exists to prevent duplicates
                        exists = ManufacturerRelationship.objects.filter(partNumber=partNumber)
                        if exists:
                            raise forms.ValidationError('Manufacturer part number already exists!')
        return self.cleaned_data
    
ManufacturerFormSet = inlineformset_factory(Part, ManufacturerRelationship,
                                            form=ManufacturerForm, extra=1,
                                            formset=CustomFormset)

class LocationForm(ModelForm):
    location = forms.ModelChoiceField(queryset=Location.objects.order_by('name'))
    class Meta:
        model = LocationRelationship
        exclude = ('part',)
        
LocationFormSet = inlineformset_factory(Part, LocationRelationship,
                                        form=LocationForm, extra=1)

class VendorForm(ModelForm):
    class Meta:
        model = Vendor
        exclude = ()
        help_texts = {
            "phone": "(10 digit number)"
        }

    def clean(self):
        super(VendorForm, self).clean()
        url = self.cleaned_data.get('web_address', None)
        #redirecting to url in template requires it to include http:// or https://
        if url:
            if 'http' not in url: 
                raise forms.ValidationError('Please enter url prefaced with http://')
        else:
            pass
        return self.cleaned_data
        
class ProductForm(ModelForm):
    class Meta:
        model = Product
        exclude = ('part', 'component_product', 'location')

    def clean(self):
        super(ProductForm, self).clean()
        url = self.cleaned_data.get('url', None)
        #redirecting to product url in template requires it to include http:// or https://
        if url:
            if 'http' not in url: 
                raise forms.ValidationError('Please enter url prefaced with http://')
        else:
            pass
        return self.cleaned_data
        
class PartToProductForm(ModelForm):
    #used to narrow down part selection dropdown with javascript
    #mark_safe - lets you added html elements to text
    search = forms.CharField(required=False, help_text=mark_safe('(Can search part type,' +
                             ' description, engimusing part number, manufacturer part number, ' +
                             'or manufacturer name) <br> Type in search value, then click out of field '+
                             'and the part dropdown will be filtered.'))
    class Meta:
        model = PartAmount
        exclude = ('product',)

PartToProductFormSet = inlineformset_factory(Product, PartAmount,
                                    form=PartToProductForm, extra=1)

class ProductToProductForm(ModelForm):
    to_product = forms.ModelChoiceField(label='Product', queryset=Product.objects.all())
    class Meta:
        model = ProductAmount
        exclude = ('from_product',)

#include fk_name because m2m relationship between self (products)
ProductToProductFormSet = inlineformset_factory(Product, ProductAmount, fk_name='from_product',
                                                form=ProductToProductForm, extra=1)
        
class ProductLocationForm(ModelForm):
    location=forms.ModelChoiceField(queryset=Location.objects.order_by('name'))
    class Meta:
        model = ProductLocation
        exclude = ('product',)

ProductLocationFormSet = inlineformset_factory(Product, ProductLocation,
                                        form=ProductLocationForm, extra=1)

class ManufacturingOrderForm(ModelForm):    
    class Meta:
        model = ManufacturingOrder
        exclude = ('product',)
        
class ManufacturingProductForm(ModelForm):
    product=forms.ModelChoiceField(queryset=Product.objects.order_by('description'))
    class Meta:
        model = MOProduct
        exclude = ()
        
ManufacturingProductFormSet = inlineformset_factory(ManufacturingOrder, MOProduct,
                                        form=ManufacturingProductForm, extra=1)
        
class TypeForm(ModelForm):
    class Meta:
        model = Type
        exclude = ()
        labels = {
            "name": "Type Name"
        }

class FieldForm(ModelForm):
    class Meta:
        model = Field
        exclude = ('fields',)
        labels = {
            "name": "Field Name",
        }

class CustomInlineFormset(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return

        names = []
        duplicates = False
        
        for form in self.forms:
           if form.cleaned_data:
               name = form.cleaned_data['name']

               if name:
                   if name in names:
                       duplicates = True
                   names.append(name)
                #ensure no 2 fields are named the same
               if duplicates:
                   raise forms.ValidationError('Fields must have unique names and types.')
                        

FieldFormSet = inlineformset_factory(Type, Field, form=FieldForm, extra=35, max_num=35,
                                     formset=CustomInlineFormset)

#edit part type requires field types to be selected
class EditFieldForm(ModelForm):
    class Meta:
        model = Field
        exclude = ()
        labels = {
            "name": "Field Name",
            "fields": "Field Type",
        }

class EditCustomInlineFormset(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return

        names = []
        fields = []
        duplicates = False
        
        for form in self.forms:
           if form.cleaned_data:
               name = form.cleaned_data['name']
               field = form.cleaned_data['fields']

               if name and field:
                   if name in names:
                       duplicates = True
                   names.append(name)

                   if field in fields:
                       duplicates = True
                   fields.append(field)
                   
                #ensure no duplicate names or fields
               if duplicates:
                   raise forms.ValidationError('Fields must have unique names and types.')
               if name and not field:
                   raise forms.ValidationError('All field names must have an associated type.')
               elif field and not name:
                   raise forms.ValidationError('All field names must have an associated type.')

                        
EditFieldFormSet = inlineformset_factory(Type, Field, form=EditFieldForm, extra=35, max_num=35,
                                     formset=EditCustomInlineFormset)

class QuickTypeForm(forms.Form):
        fields = forms.CharField()

#used in case duplicate manufacturers are created        
class MergeVendorsForm(forms.Form):
        primary = forms.ModelChoiceField(label='Primary Vendor',
                                         queryset = Vendor.objects.order_by('name'))
        alias = forms.ModelChoiceField(label='Vendor To Delete',
                                         queryset = Vendor.objects.order_by('name'))

class MergeLocationsForm(forms.Form):
        primary = forms.ModelChoiceField(label='Primary Location',
                                         queryset = Location.objects.order_by('name'))
        alias = forms.ModelChoiceField(label='Location To Delete',
                                         queryset = Location.objects.order_by('name'))

#used in part list view to filter parts displayed in table
class FilterForm(forms.Form):
        def __init__(self,*args,**kwargs):
                models = kwargs.pop('models')
                type_id = kwargs.pop('type_id')
                partType = Type.objects.get(id=type_id)
                super(FilterForm, self).__init__(*args, **kwargs)
                self.fields['location'].queryset = Location.objects.filter(part__partType=partType).distinct()
                self.fields['manufacturer'].queryset = Vendor.objects.filter(part__partType=partType).distinct()
                for field, name in models.items():
                        self.fields[field] = forms.ModelMultipleChoiceField(Part.objects.filter(partType=partType).values_list(field, flat=True).distinct(), required=False)
                        self.fields[field].label = name
                
        search = forms.CharField(required=False)
        location = forms.ModelMultipleChoiceField(required=False, queryset = Location.objects.none())
        manufacturer = forms.ModelMultipleChoiceField(required=False, queryset = Vendor.objects.none())                    

class PurchaseOrderForm(ModelForm):
    class Meta:
        model = PurchaseOrder
        exclude = ('part',)

class POPartForm(ModelForm):
    #used to narrow down part selection dropdown with javascript
    #mark_safe - lets you added html elements to text
    search = forms.CharField(required=False, help_text=mark_safe('(Can search part type,' +
                             ' description, engimusing part number, manufacturer part number, ' +
                             'or manufacturer name) <br> Type in search value, then click out of field '+
                             'and the part dropdown will be filtered.'))
    class Meta:
        model = PurchaseOrderParts
        exclude = ('purchase_order',)
        
       
POPartFormSet = inlineformset_factory(PurchaseOrder, PurchaseOrderParts, form=POPartForm, extra=1)

class APIForm(forms.Form):
        website = forms.ChoiceField(choices = ([('Digi-Key','Digi-Key'),('Mouser','Mouser')]), required=True)
        barcode = forms.CharField(label='Barcode', widget=forms.TextInput(attrs={'autofocus': True}),
                                     help_text='(MFG P/N Barcode for Mouser)', required=False)
        partNumber = forms.CharField(label='Digi-Key Part Number', help_text='(Digi-Key only)', required=False)
        manuPartNumber = forms.CharField(label='Manufacturer Part Number', required=False)

        def clean(self):
                super(APIForm, self).clean()
                barcode = self.cleaned_data.get('barcode', None)
                partNumber = self.cleaned_data.get('partNumber', None)
                manuPartNumber = self.cleaned_data.get('manuPartNumber', None)
                website = self.cleaned_data.get('website', None)
                related_fields = [barcode, partNumber, manuPartNumber]
                related_fields_selected = [field for field in related_fields if field]

                #check if more than one related fields was selected
                if len(related_fields_selected)>1: 
                   raise forms.ValidationError('Please enter only one of Barcode, Digi-Key Part Number, and Manufacturer Part Number!')
                #check that if mouser is selected, a part number isn't input(no functionality for this)
                if website == "Mouser" and partNumber:
                    raise forms.ValidationError('Can\'t enter a mouser part number, must be a manufacturer number for Mouser.')
                return self.cleaned_data

"""api requires tokens to operate, can save them here to make it easier to switch b/w
production and development since they share tokens"""
class EnterTokensForm(forms.Form):
        access_token = forms.CharField()
        refresh_token = forms.CharField()
     
        
