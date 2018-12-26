from django import forms
from mrp_system.models import Location, LocationRelationship, Part, Manufacturer, ManufacturerRelationship, Field, Type
from django.forms import ModelForm, BaseInlineFormSet
from django.forms.models import inlineformset_factory

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
           # self.fields.pop('partType')
##            self.fields['partType'].initial = partType
##            self.fields['partType'].widget.attrs['readonly'] = True
##            self.fields['partType'].widget.attrs['disabled'] = True

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
    
ManufacturerFormSet = inlineformset_factory(Part, ManufacturerRelationship,
                                            form=ManufacturerForm, extra=1)

class LocationForm(ModelForm):
    location = forms.ModelChoiceField(queryset=Location.objects.order_by('name'))
    class Meta:
        model = LocationRelationship
        exclude = ('part',)
        
LocationFormSet = inlineformset_factory(Part, LocationRelationship,
                                        form=LocationForm, extra=1)
        

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

                        

FieldFormSet = inlineformset_factory(Type, Field, form=FieldForm, extra=17, max_num=17,
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
                super(FilterForm, self).__init__(*args, **kwargs)
                self.fields['location'].queryset = Location.objects.filter(part__partType=Type.objects.get(name=typeName)).distinct()
                self.fields['manufacturer'].queryset = Manufacturer.objects.filter(part__partType=Type.objects.get(name=typeName)).distinct()
                for field, name in models.items():
                        self.fields[field] = forms.ModelMultipleChoiceField(Part.objects.all().values_list(field, flat=True).distinct(), required=False)
                        self.fields[field].label = name
                
        search = forms.CharField(required=False)
        location = forms.ModelMultipleChoiceField(required=False, queryset = Location.objects.none())
        manufacturer = forms.ModelMultipleChoiceField(required=False, queryset = Manufacturer.objects.none())

class EnterPartForm(forms.Form):
        url = forms.CharField()
        partType = forms.ModelChoiceField(queryset=Type.objects.all())
        
