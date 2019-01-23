from django import forms
from mrp_system.models import (Location, LocationRelationship,
Part, Manufacturer, ManufacturerRelationship, Field, Type, Product,
                               PartAmount, ProductAmount, ProductLocation,
                               MOProduct, ManufacturingOrder)
from django.forms import ModelForm, BaseInlineFormSet
from django.forms.models import inlineformset_factory
from timepiece.forms import TimepieceSplitDateTimeField
from django.contrib.postgres.search import SearchVector
from django.utils.safestring import mark_safe


FIELD_TYPES = {
    'char1': forms.CharField,
    'char2': forms.CharField,
    'char3': forms.CharField,
    'char4': forms.CharField,
    'char5': forms.CharField,
    'char6': forms.CharField,
    'char7': forms.CharField,
    'char8': forms.CharField,
    'char9': forms.CharField,
    'char10': forms.CharField,
    'char11': forms.CharField,
    'char12': forms.CharField,
    'char13': forms.CharField,
    'char14': forms.CharField,
    'char15': forms.CharField,
    'char16': forms.CharField,
    'char17': forms.CharField,
    'char18': forms.CharField,
    'char19': forms.CharField,
    'char20': forms.CharField,
    'integer1': forms.IntegerField,
    'integer2': forms.IntegerField
    }
FIELDS_F = {
    'char1': 'char1',
    'char2': 'char2',
    'char3': 'char3',
    'char4': 'char4',
    'char5': 'char5',
    'char6': 'char6',
    'char7': 'char7',
    'char8': 'char8',
    'char9': 'char9',
    'char10': 'char10',
    'char11': 'char11',
    'char12': 'char12',
    'char13': 'char13',
    'char14': 'char14',
    'char15': 'char15',
    'char16': 'char16',
    'char17': 'char17',
    'char18': 'char18',
    'char19': 'char19',
    'char20': 'char20',
    'integer1': 'integer1',
    'integer2': 'integer2'
    }

class PartForm(ModelForm):
##    class Meta:
##        model = Part
##        exclude = ('manufacturer',)  

        def __init__(self, type_id, *args, **kwargs):
            super(PartForm, self).__init__(*args, **kwargs)
            #type_id = kwargs.pop('type_id', 0)
            partType = Type.objects.get(id=type_id)

            for field in partType.field.all():
                #self.fields[field.name] = FIELD_TYPES[field.fields](label = field.name)
                self.fields[FIELDS_F[field.fields]].label = field.name
            #parts = partType.field.all()
            extra_fields = ('char1', 'char2', 'char3', 'char4', 'char5', 'char6',
                            'char7', 'char8','char9','char10','char11','char12',
                            'char13','char14','char15','char16','char17','char18',
                            'char19','char20','integer1', 'integer2')
            for field in extra_fields:
                if field not in partType.field.values_list('fields', flat=True):
                    self.fields.pop(field)
            
        class Meta:
            model = Part
            exclude = ('manufacturer', 'location', 'partType')
            

class ManufacturerForm(ModelForm):
    manufacturer = forms.ModelChoiceField(queryset=Manufacturer.objects.order_by('name'))
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
        #password2 = self.cleaned_data.get('password2', None)
                try:
                        mr = ManufacturerRelationship.objects.get(part=self.instance)
                        number = mr.partNumber
                except ManufacturerRelationship.DoesNotExist:
                    mr = None
                    number = None
                
                if partNumber == number:
                        pass
                else:
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
class ProductForm(ModelForm):
    class Meta:
        model = Product
        exclude = ('part', 'component_product', 'location')

    def clean(self):
        super(ProductForm, self).clean()
        url = self.cleaned_data.get('url', None)

        if url:
            if 'http' not in url: 
                raise forms.ValidationError('Please enter url prefaced with http://')
        else:
            pass
        return self.cleaned_data
        
class PartToProductForm(ModelForm):
    search = forms.CharField(required=False, help_text=mark_safe('(Can search part type,' +
                             ' description, engimusing part number, manufacturer part number, ' +
                             'or manufacturer name) <br> Type in search value, then click out of field '+
                             'and the part dropdown will be filtered.'))
    #part = forms.ModelChoiceField(queryset=Part.objects.none())
    class Meta:
        model = PartAmount
        exclude = ('product',)

##    def __init__(self, *args, **kwargs):
##        super().__init__(*args, **kwargs)
##        self.fields['part'].queryset = Part.objects.none()
##
##        if 'search' in self.data:
##            print("yes")
##            try:
##                searchField = self.data.get('search')
##                print(searchField + "search")
##                self.fields['part'].queryset = Part.objects.annotate(search=SearchVector('partType__name', 'description'),).filter(search=searchField)
##
##            except (ValueError, TypeError):
##                pass  # invalid input from the client; ignore and fallback to empty City queryset
##        elif self.instance.pk:
##            self.fields['part'].queryset = Part.objects.annotate(search=SearchVector('partType__name', 'description'),).filter(search=self.instance.search)
##            #self.instance.country.city_set.order_by('name')

PartToProductFormSet = inlineformset_factory(Product, PartAmount,
                                    form=PartToProductForm, extra=1)

class ProductToProductForm(ModelForm):
    to_product = forms.ModelChoiceField(label='Product', queryset=Product.objects.all())
    class Meta:
        model = ProductAmount
        exclude = ('from_product',)

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
        exclude = ()
        labels = {
            "name": "Field Name",
            "fields": "Field Type"
        }

class CustomInlineFormset(BaseInlineFormSet):
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

               if duplicates:
                   raise forms.ValidationError('Fields must have unique names and types.')
               if name and not field:
                   raise forms.ValidationError('All field names must have an associated type.')
               elif field and not name:
                   raise forms.ValidationError('All field names must have an associated type.')

                        

FieldFormSet = inlineformset_factory(Type, Field, form=FieldForm, extra=20, max_num=20,
                                     formset=CustomInlineFormset)

class TypeSelectForm(forms.Form):
    partType = forms.ModelChoiceField(label='', queryset=Type.objects.order_by('name'),
                                widget=forms.Select(attrs={"onChange":'this.form.submit()'}))

    def save(self):
        return (self.cleaned_data.get('partType'))

class MergeManufacturersForm(forms.Form):
        primary = forms.ModelChoiceField(label='Primary Manufacturer',
                                         queryset = Manufacturer.objects.order_by('name'))
        alias = forms.ModelChoiceField(label='Manufacturer To Delete',
                                         queryset = Manufacturer.objects.order_by('name'))

class MergeLocationsForm(forms.Form):
        primary = forms.ModelChoiceField(label='Primary Location',
                                         queryset = Location.objects.order_by('name'))
        alias = forms.ModelChoiceField(label='Location To Delete',
                                         queryset = Location.objects.order_by('name'))

class FilterForm(forms.Form):
        def __init__(self,*args,**kwargs):
                models = kwargs.pop('models')
                typeName = kwargs.pop('typeName')
                partType = Type.objects.get(name=typeName)
                super(FilterForm, self).__init__(*args, **kwargs)
                self.fields['location'].queryset = Location.objects.filter(part__partType=partType).distinct()
                self.fields['manufacturer'].queryset = Manufacturer.objects.filter(part__partType=partType).distinct()
                for field, name in models.items():
                        self.fields[field] = forms.ModelMultipleChoiceField(Part.objects.filter(partType=partType).values_list(field, flat=True).distinct(), required=False)
                        self.fields[field].label = name
                
        search = forms.CharField(required=False)
        location = forms.ModelMultipleChoiceField(required=False, queryset = Location.objects.none())
        manufacturer = forms.ModelMultipleChoiceField(required=False, queryset = Manufacturer.objects.none())

                        
class MouserForm(forms.Form):
        partNumber = forms.CharField(label='Part Number')
        partType = forms.ModelChoiceField(queryset=Type.objects.order_by('name'))

class APIForm(forms.Form):
        website = forms.ChoiceField(choices = ([('Digi-Key','Digi-Key'),('Mouser','Mouser')]), required=True)
        barcode = forms.CharField(label='Barcode', widget=forms.TextInput(attrs={'autofocus': True}),
                                     help_text='(MFG P/N Barcode for Mouser)', required=False)
        partNumber = forms.CharField(label='Digi-Key Part Number', help_text='(Digi-Key only)', required=False)
        manuPartNumber = forms.CharField(label='Manufacturer Part Number', required=False)
        partType = forms.ModelChoiceField(queryset=Type.objects.order_by('name'), label='Part Type')

        def clean(self):
                super(APIForm, self).clean()
                barcode = self.cleaned_data.get('barcode', None)
                partNumber = self.cleaned_data.get('partNumber', None)
                manuPartNumber = self.cleaned_data.get('manuPartNumber', None)
                related_fields = [barcode, partNumber, manuPartNumber]
                related_fields_selected = [field for field in related_fields if field]

        # check if more than one related fields was selected 
                if len(related_fields_selected)>1: 
                   raise forms.ValidationError('Please enter only one of Barcode, Digi-Key Part Number, and Manufacturer Part Number!')
                return self.cleaned_data

        
        
