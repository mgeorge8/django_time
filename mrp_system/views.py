from django.shortcuts import render, get_object_or_404, redirect
from django.http import (HttpResponse, HttpResponseRedirect, HttpResponseNotFound,
                         JsonResponse)
from django.views.generic import ListView, TemplateView
from mrp_system.models import (Part, Type, Field, Vendor,
                               ManufacturerRelationship, Location,
                               LocationRelationship, DigiKeyAPI,
                               PartAmount, Product, ProductAmount, ManufacturingOrder,
                               MOProduct, ProductLocation)
from mrp_system.forms import (FilterForm, PartForm, LocationForm, LocationFormSet,
                              MergeLocationsForm, ManufacturerFormSet,
                              MergeVendorsForm, FieldFormSet, TypeForm, APIForm,
                              ProductForm, PartToProductFormSet, PartToProductForm,
                              ProductToProductFormSet, ProductLocationFormSet,
                              ManufacturingOrderForm, ManufacturingProductFormSet,
                              EditFieldFormSet, QuickTypeForm, EnterTokensForm)
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.forms.models import inlineformset_factory
from django.urls import reverse, reverse_lazy
from django.forms import ModelForm
from django import forms
from django.db.models.functions import Cast
from django.db.models import CharField, Sum
from django.contrib.postgres.search import SearchVector
from django.core.files.storage import DefaultStorage
import requests, json, urllib, xlsxwriter, io, sys, re, time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils.safestring import mark_safe
from itertools import chain

class TypeListView(ListView):
    model = Type
    template_name = 'type_list.html'
    ordering = ['name']

#takes in list of type name, prefix and fields for fast entry
def quick_type_create(request):
    if request.method == 'POST':
        form = QuickTypeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['fields']
            #split up data and process it
            data = data.split(",")
            typeName = data.pop(0).strip()
            suffix = data.pop(0).strip()
            fields = {}
            number = 1
            #assign each field to a character field up to 35
            for d in data:
                if number > 35:
                    messages.warning(request, ('Part model can only track 35 fields.'))
                    url = reverse('quick_type')
                    return HttpResponseRedirect(url)
                fields[d.strip()] = "char"+str(number)
                number += 1
            #create type and field models    
            partType = Type.objects.create(name=typeName, prefix=suffix)
            for name, field in fields.items():
                Field.objects.create(name=name, fields=field, typePart=partType)
            redirect_url = reverse('edit_type', args=[partType.pk])
            return HttpResponseRedirect(redirect_url)
    else:
        form = QuickTypeForm()
    return render(request,'quick_type_form.html',{'form': form})

class TypeCreate(CreateView):
    form_class = TypeForm
    template_name = 'type_form.html'
    success_url = reverse_lazy('list_types')

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        field_formset = FieldFormSet()
        hint = "Enter Part Type name, Prefix for Engimusing Part Number, "
        hint += "and name of each individual field to be tracked (excluding description, "
        hint += "part numbers, manufacturer, location, and stock)."
        return render(request, self.template_name, {'form': form,
                                                    'field_formset': field_formset,
                                                    'hint': hint})

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        field_formset = FieldFormSet(request.POST)
        if (form.is_valid() and field_formset.is_valid()):
            return self.form_valid(form, field_formset)
        else:
            return self.form_invalid(form, field_formset)

    def form_valid(self, form, field_formset):
        self.object = form.save()
        field_formset.instance = self.object
        forms = field_formset.save(commit=False)
        count = 1
        """assign field names to fields, don't need to check for 35 because
        only allows 35 fields in form"""
        for f in forms:
            f.fields = 'char' + str(count)
            count += 1
            f.save()
        return super(TypeCreate, self).form_valid(form)

    def form_invalid(self, form, field_formset):
        return self.render_to_response(
            self.get_context_data(form=form, field_formset=field_formset))

class EditType(UpdateView):
    model = Type
    form_class = TypeForm
    pk_url_kwarg = 'type_id'
    template_name = 'type_form.html'
    success_url = reverse_lazy('list_types')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        field_formset = EditFieldFormSet(instance=self.object)
        hint = "Enter Part Type name, Prefix for Engimusing Part Number, "
        hint += "and name of each individual field to be tracked (excluding description, "
        hint += "part numbers, manufacturer, location, and stock). \n"
        hint += "Ensure each field has a different Character field type selected!"
        return render(request, self.template_name, {'form': form,
                                                    'field_formset': field_formset,
                                                    'hint': hint})

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        field_formset = EditFieldFormSet(request.POST, instance=self.object)
        if (form.is_valid() and field_formset.is_valid()):
            return self.form_valid(form, field_formset)
        else:
            return self.form_invalid(form, field_formset)

    def form_valid(self, form, field_formset):
        self.object = form.save()
        #must save parent model first and then use it to save child models
        field_formset.instance = self.object
        field_formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, field_formset):
        return self.render_to_response(
            self.get_context_data(form=form, field_formset=field_formset))

class DeleteType(DeleteView):
    model = Type
    success_url = reverse_lazy('list_types')
    pk_url_kwarg = 'type_id'
    template_name = 'delete_type.html' 

def PartCreate(request, type_id):
    partType = Type.objects.get(id=type_id)

    if request.method == 'POST':
        #must pass request.FILES for datasheets
        form = PartForm(type_id, request.POST, request.FILES)
        manu_formset = ManufacturerFormSet(request.POST)
        location_formset = LocationFormSet(request.POST)
        if form.is_valid() and manu_formset.is_valid() and location_formset.is_valid():
            self_object = form.save(commit=False)
            #add the part type to part
            self_object.partType_id = type_id
            self_object.save()
            #assign part to location and manufacturer relationship
            location_formset.instance = self_object
            location_formset.save()
            manu_formset.instance = self_object
            manu_formset.save()
            url = reverse('list_parts', args=[partType.pk])
            return HttpResponseRedirect(url)
    else:
        form = PartForm(type_id=type_id)
        manu_formset = ManufacturerFormSet()
        location_formset = LocationFormSet()
    return render(request,'part_form.html',{'part_form': form,
                                            'location_formset': location_formset,
                                            'manu_formset': manu_formset,
                                            'partType': partType})

def PartEdit(request, type_id, id):
    partType = Type.objects.get(id=type_id)
    instance = get_object_or_404(Part, id=id)

    if request.method == 'POST':
        form = PartForm(type_id, request.POST, request.FILES, instance=instance)
        manu_formset = ManufacturerFormSet(request.POST, instance=instance)
        location_formset = LocationFormSet(request.POST, instance=instance)
        if form.is_valid():
            part = form.save(commit=False)
            part.partType_id = type_id
            if manu_formset.is_valid() and location_formset.is_valid():
                part.save()
                manu_formset.save()
                location_formset.save()
                url = reverse('list_parts', args=[partType.pk])
                return HttpResponseRedirect(url)
    else:
        form = PartForm(type_id=type_id, instance=instance)
        manu_formset = ManufacturerFormSet(instance=instance)
        location_formset = LocationFormSet(instance=instance)
    return render(request,'part_form.html',{'part_form': form,
                                            'location_formset': location_formset,
                                            'manu_formset': manu_formset,
                                            'partType': partType})

def ListParts(request, type_id):
    filters={}
    partType = Type.objects.get(id=type_id)
    parts = Part.objects.filter(partType=partType)
    fields = Field.objects.filter(typePart_id=type_id)
    #list of all possible fields
    list_fields = ['manufacturer','location']
    for x in range(1,36):
        list_fields.append('char' + str(x))
    name = ''
    for field in fields:
        if field.fields == "char1":
            name = field.name
    searchField = None
    models={}
    for field in fields:
        models[field.fields] = field.name
    if request.method == 'POST':
        #pass list of fields and field names for part type to filter form
        form = FilterForm(request.POST, models=models, type_id=type_id)
        #add all filters that have been selected
        for n in list_fields:
            if request.POST.getlist(n):
                filters[n + '__in'] = request.POST.getlist(n)
        searchField = request.POST.get('search')
        #reset a blank form that could be filtered again
        form=FilterForm(models=models, type_id=type_id)
    else:
        form = FilterForm(models=models, type_id=type_id)
    #apply filters to part list
    parts = parts.filter(**filters)
    #create list of current filters to notify user
    string_filters = 'Current Filters: '
    for key, value in filters.items():
        if key == 'location__in':
            locations = Location.objects.filter(id__in=value)
            string_filters += ", ".join(l.name for l in locations) + '; '
        elif key == 'manufacturer__in':
            manufacturers = Vendor.objects.filter(id__in=value)
            string_filters += ", ".join(m.name for m in manufacturers) + '; '
        else:
            string_filters += ", ".join(v for v in value) + '; '
    string_filters += "\t Search Field: "
    if searchField:
        string_filters += searchField
    if searchField == "" or searchField is None:
        parts = parts.distinct('id')
    else:
        #apply search field
        parts = parts.annotate(search=SearchVector('manufacturer__name', 'location__name', 'description',
                                                   'engimusingPartNumber', 'manufacturerrelationship__partNumber',
                                                   'char1', 'char2','char3','char4','char5','char6','char7','char8',
                                                   'char9','char10','char11','char12','char13','char14','char15',
                                                   'char16','char17','char18','char19','char20','char21','char22',
                                                   'char23','char24','char25','char26','char27','char28','char29',
                                                   'char30','char31','char32','char33','char34','char35')).filter(search=searchField)
        parts = parts.distinct('id')
    return render(request, 'part_list.html', {'type': partType, 'parts': parts,
                                              'fields': fields, 'form': form,
                                              'name': name, 'string_filters': string_filters})

class DeletePart(DeleteView):
    model = Part
    success_url = reverse_lazy('list_types')
    pk_url_kwarg = 'part_id'
    template_name = 'delete_part.html'
    
class VendorListView(ListView):
    template_name = 'vendor_list.html'
    context_object_name = 'all_manufacturers'

    def get_queryset(self):
        return Vendor.objects.filter(vendor_type='manufacturer').order_by('name')

    def get_context_data(self, **kwargs):
        context = super(VendorListView, self).get_context_data(**kwargs)
        context['distributors'] = Vendor.objects.filter(vendor_type='distributor').order_by('name')
        return context

class LocationListView(ListView):
    model = Location
    template_name = 'location_list.html'
    ordering = ['name']

class CreateVendor(CreateView):
    model = Vendor
    fields = ['name','vendor_type','address','phone','web_address']
    template_name = 'vendor_form.html'
    success_url = reverse_lazy('list_vendors')

    def get_context_data(self, **kwargs):
        #pass list of already created manufacturer to template to list under form
        kwargs['vendors'] = Vendor.objects.order_by('name')
        return super(CreateVendor, self).get_context_data(**kwargs)

class CreateLocation(CreateView):
    model = Location
    fields = ['name']
    template_name = 'location_form.html'
    success_url = reverse_lazy('list_locations')

    def get_context_data(self, **kwargs):
        kwargs['locations'] = Location.objects.order_by('name')
        return super(CreateLocation, self).get_context_data(**kwargs)

class VendorUpdate(UpdateView):
    model = Vendor
    fields = ['name','vendor_type','address','phone','web_address']
    pk_url_kwarg = 'vendor_id'
    template_name = 'update_vendor.html'
    success_url = reverse_lazy('list_vendors')

class LocationUpdate(UpdateView):
    model = Location
    fields = ['name']
    pk_url_kwarg = 'location_id'
    template_name = 'update_location.html'
    success_url = reverse_lazy('list_locations')

#used in part list to quickly edit location and stock
def LocationRelationshipEdit(request, locationrelationship_id):
    rel = get_object_or_404(LocationRelationship, id=locationrelationship_id)
    partType = Type.objects.get(part=rel.part)
    if request.method == "POST":
        form = LocationForm(request.POST, instance=rel)
        if form.is_valid():
            form.save()
            nextUrl = request.POST.get('next', '/')
            return HttpResponseRedirect(nextUrl)
    else:
        form = LocationForm(instance=rel)
    return render(request, 'update_loc_relationship.html', {'form': form,
                                                            'loc_rel': rel,
                                                            'partType': partType})
#used in part list to quickly add location and stock if there isn't one
def LocationRelationshipAdd(request, part_id):
    part = get_object_or_404(Part, id=part_id)
    partType = Type.objects.get(part=part)
    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.cleaned_data['location']
            stock = form.cleaned_data['stock']
            LocationRelationship.objects.create(part=part, location=location, stock=stock)
            nextUrl = request.POST.get('next', '/')
            return HttpResponseRedirect(nextUrl)
    else:
        form = LocationForm()
    return render(request, 'add_loc_relationship.html', {'form': form, 'partType': partType})

class LocationRelationshipDelete(DeleteView):
    model = LocationRelationship
    pk_url_kwarg = 'locationrelationship_id'    
    template_name = 'delete_location.html'

    def get_success_url(self):
        #redirect to part list view for part type
        loc_id=self.kwargs['locationrelationship_id']
        rel = get_object_or_404(LocationRelationship, id=loc_id)
        partType = Type.objects.get(part=rel.part)
        return reverse_lazy('list_parts', kwargs={'type_id': partType.id})

class VendorDelete(DeleteView):
    model = Vendor
    pk_url_kwarg = 'vendor_id'
    template_name = 'delete_vendor.html'
    success_url = reverse_lazy('list_vendors')

class LocationDelete(DeleteView):
    model = Location
    pk_url_kwarg = 'location_id'
    template_name = 'delete_location.html'
    success_url = reverse_lazy('list_locations')

#takes in 2 objects and passes to mergeVendor function
def MergeVendorView(request):
    if request.method == "POST":
        form = MergeVendorsForm(request.POST)
        if form.is_valid():
            primary_object = form.cleaned_data['primary']
            alias_object = form.cleaned_data['alias']
            if not isinstance(alias_object, Vendor):
                raise TypeError('Only Vendor instances can be merged')
            
            if not isinstance(primary_object, Vendor):
                raise TypeError('Only Vendor instances can be merged')

            type_alias = alias_object.vendor_type
            type_primary = primary_object.vendor_type
            if type_alias != "manufacturer" or type_primary != "manufacturer":
                messages.warning(request,'Vendors must be of manufacturer type to be merged.')
                return redirect(reverse('merge_vendors'))

            #replace all instance of alias vendor with primary vendor
            parts = alias_object.part_set.all()
            partNumber = []
            partSet = []
            #get all needed information from alias_object
            for part in parts:
                m = ManufacturerRelationship.objects.get(part=part, manufacturer=alias_object)
                partNumber.append(m.partNumber)
                partSet.append(m.part)
            alias_object.part_set.clear()
            length = len(partSet)
            #set all alias_object relationships to primary object
            for x in range(length):
                ManufacturerRelationship.objects.create(part=partSet[x],
                                                        manufacturer=primary_object,
                                                        partNumber=partNumber[x])
            alias_object.delete()
            return redirect('list_vendors')
    else: form = MergeVendorsForm()
    return render(request, "merge_vendors.html", {"form":form})


def MergeLocationView(request):
    if request.method == "POST":
        form = MergeLocationsForm(request.POST)
        if form.is_valid():
            primary_object = form.cleaned_data['primary']
            alias_object = form.cleaned_data['alias']
            MergeLocation(primary_object, alias_object)
            return redirect('list_locations')
    else: form = MergeLocationsForm()
    return render(request, "merge_locations.html", {"form":form})

def MergeLocation(primary_object, alias_object):
    #ensure objects are of type Location
    if not isinstance(alias_object, Location):
        raise TypeError('Only Location instances can be merged')
    
    if not isinstance(primary_object, Location):
        raise TypeError('Only Location instances can be merged')

    parts = alias_object.part_set.all()
    stock = []
    partSet = []
    #get all needed information from alias_object
    for part in parts:
        l = LocationRelationship.objects.get(part=part, location=alias_object)
        stock.append(l.stock)
        partSet.append(l.part)
    alias_object.part_set.clear()
    length = len(partSet)
    #set all alias_object relationships to primary object
    for x in range(length):
        LocationRelationship.objects.create(part=partSet[x],
                                            location=primary_object,
                                            stock=stock[x])
    alias_object.delete()


import http.client

def enter_digi_part(request):
    if request.method == "POST":
        form = APIForm(request.POST)
        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            partNumber = form.cleaned_data['partNumber']
            manuPartNumb = form.cleaned_data['manuPartNumber']
            website = form.cleaned_data['website']
            #this model holds the access and refresh token for digikey API
            digi = DigiKeyAPI.objects.get(name="DigiKey")
            
            #get new access token with refresh token
            API_ENDPOINT = "https://sso.digikey.com/as/token.oauth2"

            data = {'client_id': '73432ca9-e8ba-4965-af17-a22107f63b35',
                    'client_secret': 'G2rQ1cM8yM4gV6rW2nA1wL2yF7dN4sX4fJ2lV6jE5uT0bB0uG8',
                    'refresh_token': digi.refresh_token,
                    'grant_type': 'refresh_token'
                    }
            r = requests.post(url = API_ENDPOINT, data=data)
            response = r.json()
            try:
                refreshToken = response['refresh_token']
            except (IndexError, KeyError):
                messages.warning(request, ('Digi-Key access tokens are off.'))
                url = reverse('digi_part')
                return HttpResponseRedirect(url)

            #set access and refresh token from tokens returned with API
            accessToken = response['access_token']
            setattr(digi,"refresh_token",refreshToken)
            setattr(digi,"access_token",accessToken)
            digi.save()
            #if digikey barcode, use barcode api to get part number
            if website == 'Digi-Key' and barcode:
                conn = http.client.HTTPSConnection("api.digikey.com")

                headers = {
                    'x-ibm-client-id': '73432ca9-e8ba-4965-af17-a22107f63b35',
                    'authorization': digi.access_token,
                    'accept': "application/json"
                    }

                conn.request("GET", "/services/barcode/v1/productbarcode/" + barcode, headers=headers)

                res = conn.getresponse()
                data = res.read().decode("utf-8")
                part = json.loads(data)
                partNumber = part['DigiKeyPartNumber']
                search = partNumber

            #if mouser barcode, its a manufacturer number
            elif website == 'Mouser' and barcode:
                search = barcode
                
            elif partNumber:
                search = partNumber
            elif manuPartNumb:
                search = manuPartNumb
                
            else:
                return HttpResponseNotFound('<h1>Must select a website and enter a field!</h1>')

            #get part information from part number or manufacturer part number
            conn = http.client.HTTPSConnection("api.digikey.com")

            payload = "{\"SearchOptions\":[\"ManufacturerPartSearch\"],\"Keywords\":\"" + search + "\",\"RecordCount\":\"10\",\"RecordStartPosition\":\"0\",\"Filters\":{\"CategoryIds\":[27442628],\"FamilyIds\":[81316194],\"ManufacturerIds\":[88520800],\"ParametricFilters\":[{\"ParameterId\":\"725\",\"ValueId\":\"7\"}]},\"Sort\":{\"Option\":\"SortByUnitPrice\",\"Direction\":\"Ascending\",\"SortParameterId\":\"50\"},\"RequestedQuantity\":\"50\"}"

            headers = {
                'x-ibm-client-id': '73432ca9-e8ba-4965-af17-a22107f63b35',
                'x-digikey-locale-site': "US",
                'x-digikey-locale-language': "en",
                'x-digikey-locale-currency': "USD",
                'authorization': digi.access_token,
                'content-type': "application/json",
                'accept': "application/json"
                }

            conn.request("POST", "/services/partsearch/v2/keywordsearch", payload, headers)

            res = conn.getresponse()
            string = res.read().decode('utf-8')
            sys.stdout.flush()
            jstr = json.loads(string)
            try:
                part = jstr['ExactDigiKeyPart']
                data = part['Parameters']
            except(IndexError, KeyError, TypeError):
                try:
                    part=jstr['ExactParts'][0]
                    data = part['Parameters']
                except(IndexError, KeyError, TypeError):
                    if website == 'Mouser' and barcode:
                        return HttpResponseNotFound('<h1>Invalid part number. Ensure the manufacturer part number exists on digi-key.</h1>')
                    else:
                        return HttpResponseNotFound('<h1>Invalid Part Number.</h1>')
            #grab all parameters returned from api
            params = {}
            for value in data:
                params[value['Parameter']] = value['Value']
            typeName = part['Family']['Text']
##            #get all words in type name, exclude -'s
##            list_name = re.findall(r'\w+', typeName)
##            #get word count
##            word_count = len(list_name)
##            #assign prefix based on amount of words in type name
##            prefix = ""
##            if word_count == 1:
##                prefix = typeName[:3].upper()
##            if word_count == 2:
##                prefix = (list_name[0][:1] + list_name[1][:2]).upper()
##            if word_count >= 3:
##                prefix = (list_name[0][:1] + list_name[1][:1] + list_name[2][:1]).upper()
            partType, created = Type.objects.get_or_create(name=typeName)
            count = 1
            #if new part type, assign prefix
            if created:
                #get all words in type name, exclude -'s
                list_name = re.findall(r'\w+', typeName)
                #get word count
                word_count = len(list_name)
                #assign prefix based on amount of words in type name
                prefix = ""
                if word_count == 1:
                    prefix = typeName[:3].upper()
                if word_count == 2:
                    prefix = (list_name[0][:1] + list_name[1][:2]).upper()
                if word_count >= 3:
                    prefix = (list_name[0][:1] + list_name[1][:1] + list_name[2][:1]).upper()
                setattr(partType,"prefix",prefix)
                partType.save()
                #series is always separate from the other parameters 
                try:
                    part['Series']['Parameter']
                    Field.objects.create(name='Series',fields='char1', typePart=partType)
                    count = 2
                except(IndexError, KeyError, TypeError):
                    count = 1
                for name, value in params.items():
                    #print("here")
                    if count <= 35:
                        field = "char" + str(count)
                        Field.objects.create(name=name, fields=field, typePart=partType)
                        count += 1
                    #part model only allows for 35 fields currently
                    else:
                        messages.warning(request, ('Can\'t create type, too many fields.'))
                        url = reverse('digi_part')
                        return HttpResponseRedirect(url)
            fields = Field.objects.filter(typePart=partType)
            description = part['DetailedDescription']
            if not description:
                description = part['ProductDescription']
            try:
                number = part['ManufacturerPartNumber']
                manufacturer = part['ManufacturerName']['Text']
            except(IndexError, KeyError, TypeError):
                number = None
                manufacturer = None
            if manufacturer:
                manu, created = Vendor.objects.get_or_create(name=manufacturer, vendor_type="manufacturer")
                #this is our way of checking for duplicates
                exists = ManufacturerRelationship.objects.filter(manufacturer=manu, partNumber=number)
                if exists:
                    messages.warning(request, ('Manufacturer Part Number already exists.'))
                    url = reverse('digi_part')
                    return HttpResponseRedirect(url)
            new_part = Part.objects.create(partType=partType, description=description)
            if manufacturer:
                ManufacturerRelationship.objects.create(part=new_part, manufacturer=manu, partNumber=number)
            for field in fields:
                name = field.name
                field_name = field.fields
                #composition parameter is formatted differently
                if field.name == "Composition":
                    try:
                        value = part['Family']['Text']
                        setattr(new_part, field.fields, value)
                    except(IndexError, KeyError):
                        pass
                try:
                    value = part[name]['Value']
                    setattr(new_part, field.fields, value)
                except(IndexError, KeyError):
                    try:
                        value = params[name]
                        setattr(new_part, field.fields, value)
                    except(IndexError, KeyError):
                        pass
            new_part.save()
            #assign datasheet if it exists
            try:
                datasheet_url = part['PrimaryDatasheet']
                if 'pdf' in datasheet_url:
                    try:
                        datasheet_name = urlparse(datasheet_url).path.split('/')[-1]
                        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:35.0) Gecko/20100101 Firefox/35.0'}
                        response = requests.get(datasheet_url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            new_part.datasheet.save(datasheet_name, ContentFile(response.content), save=True)
                    except (requests.exceptions.SSLError):
                        pass
            except(IndexError, KeyError, TypeError):
                pass
            redirect_url = reverse('edit_part', args=[partType.pk, new_part.id])
            return HttpResponseRedirect(redirect_url)
    else:
        form = APIForm()
    return render(request, "oauth.html", {'form': form})


def get_parts(request):
    searchField = request.GET.get('search')
    if searchField:
        parts = Part.objects.annotate(search=SearchVector('partType__name', 'description', 'location__name',
                                                      'engimusingPartNumber', 'manufacturer__name',
                                                      'manufacturerrelationship__partNumber'),).filter(search=searchField)
    else:
        parts = Part.objects.all()
    parts_dict = {}
    for part in parts:
        parts_dict[part.id] = part.engimusingPartNumber + " - " + part.description
    return JsonResponse(parts_dict)

def CreateProduct(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        part_formset = PartToProductFormSet(request.POST)
        product_formset = ProductToProductFormSet(request.POST)
        location_formset = ProductLocationFormSet(request.POST)
        if (form.is_valid() and part_formset.is_valid() and
            product_formset.is_valid() and location_formset.is_valid()):
            self_object = form.save()
            part_formset.instance = self_object
            part_formset.save()
            product_formset.instance = self_object
            product_formset.save()
            location_formset.instance = self_object
            location_formset.save()
            url = reverse('list_product')
            return HttpResponseRedirect(url)
    else:
        form = ProductForm()
        part_formset = PartToProductFormSet()
        product_formset = ProductToProductFormSet()
        location_formset = ProductLocationFormSet()
    return render(request,'product_create.html',{'form': form, 'part_formset': part_formset,
                                            'product_formset': product_formset, 'location_formset':
                                                 location_formset})


class ProductListView(ListView):
    model = Product
    template_name = 'product_list.html'
    ordering = ['description']
    
        
def EditProduct(request, id):
    instance = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=instance)
        part_formset = PartToProductFormSet(request.POST, instance=instance)
        product_formset = ProductToProductFormSet(request.POST, instance=instance)
        location_formset = ProductLocationFormSet(request.POST, instance=instance)
        if (form.is_valid() and part_formset.is_valid() and
            product_formset.is_valid() and location_formset.is_valid()):
            self_object = form.save()
            part_formset.instance = self_object
            part_formset.save()
            product_formset.instance = self_object
            product_formset.save()
            location_formset.instance = self_object
            location_formset.save()
            url = reverse('list_product')
            return HttpResponseRedirect(url)
    else:
        form = ProductForm(instance=instance)
        part_formset = PartToProductFormSet(instance=instance)
        product_formset = ProductToProductFormSet(instance=instance)
        location_formset = ProductLocationFormSet(instance=instance)
    return render(request,'product_create.html',{'form': form, 'part_formset': part_formset,
                                            'product_formset': product_formset,
                                                 'location_formset': location_formset})

class DeleteProduct(DeleteView):
    model = Product
    success_url = reverse_lazy('list_product')
    pk_url_kwarg = 'product_id'
    template_name = 'delete_product.html'

def ProductDetailView(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    parts = product.partamount_set.all()
    locations = product.productlocation_set.all()
    component_products = ProductAmount.objects.filter(from_product=product)
    return render(request, 'product_detail.html', {'product': product,
                                                   'locations': locations,
                                               'parts': parts,
                                                   'component_products': component_products})
def bomExcel(parts, description):
    output = io.BytesIO()
    title = "BOM-%s.xlsx" % description
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()
##    partDetail = ()
##    listDetail = []
    row = 0
    col = 0
    worksheet.write(row, col, 'Quantity')
    worksheet.write(row, col + 1, 'Engimusing Part Number')
    worksheet.write(row, col + 2, 'Manufacturer')
    worksheet.write(row, col + 3, 'Manufacturer Part Number')
    worksheet.write(row, col + 4, 'Description')
    row += 1
    for key, value in parts.items():
        worksheet.write(row, col, value)
        worksheet.write(row, col + 1, key.engimusingPartNumber)
        worksheet.write(row, col + 2, ",".join(p['manufacturer__name'] for p in
                                               key.manufacturerrelationship_set.values('manufacturer__name')))
        worksheet.write(row, col + 3, ",".join(p['partNumber'] for p in
                                               key.manufacturerrelationship_set.values('partNumber')))
        worksheet.write(row, col + 4, key.description)
        row += 1

    workbook.close()

    output.seek(0)

    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = 'attachment; filename=%s' % title

    return response                

def billOfMaterialsDetail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    parts = {}
##    mos = mo.moproduct_set.all()
##    products = ProductAmount.objects.none()   
##    for m in mos:
    partList = product.partamount_set.all()
    for p in partList:
        if parts.get(p.part):
            parts[p.part]+=p.amount
        else:
            parts[p.part]=p.amount
    products = ProductAmount.objects.filter(from_product=product)
    while products:
        productList=products
        products = ProductAmount.objects.none()
        for pr in productList:
            partList2 = pr.to_product.partamount_set.all()
            multiplier = pr.amount 
            for pa in partList2:
                if parts.get(pa.part):
                    parts[pa.part]+= (pa.amount * multiplier)
                else:
                    parts[pa.part]= (pa.amount * multiplier)
            if products:
                products = products.union(ProductAmount.objects.filter(from_product=pr.to_product))
            else:
                products = ProductAmount.objects.filter(from_product=pr.to_product)
    if(request.GET.get('mybtn')):
        return bomExcel(parts, product.description)
    return render(request, 'bom_detail.html', {'parts': parts, 'product': product}) 

def CreateMO(request):
    if request.method == 'POST':
        form = ManufacturingOrderForm(request.POST)
        manu_formset = ManufacturingProductFormSet(request.POST)
        #product_formset = ProductToProductFormSet(request.POST)
        #location_formset = ProductLocationFormSet(request.POST)
        if (form.is_valid() and manu_formset.is_valid()):
            self_object = form.save()
            manu_formset.instance = self_object
            manu_formset.save()
            url = reverse('list_mo')
            return HttpResponseRedirect(url)
    else:
        form = ManufacturingOrderForm()
        manu_formset = ManufacturingProductFormSet()
    return render(request,'mo_form.html',{'form': form, 'manu_formset': manu_formset})

class MOListView(ListView):
    model = ManufacturingOrder
    template_name = 'mo_list.html'
    ordering = ['date_created']
        
def EditMO(request, id):
    instance = get_object_or_404(ManufacturingOrder, id=id)
    if request.method == 'POST':
        form = ManufacturingOrderForm(request.POST, instance=instance)
        manu_formset = ManufacturingProductFormSet(request.POST, instance=instance)
        #product_formset = ProductToProductFormSet(request.POST)
        #location_formset = ProductLocationFormSet(request.POST)
        if (form.is_valid() and manu_formset.is_valid()):
            self_object = form.save()
            manu_formset.instance = self_object
            manu_formset.save()
            url = reverse('list_mo')
            return HttpResponseRedirect(url)
    else:
        form = ManufacturingOrderForm(instance=instance)
        manu_formset = ManufacturingProductFormSet(instance=instance)
    return render(request,'mo_form.html',{'form': form, 'manu_formset': manu_formset})

class DeleteMO(DeleteView):
    model = ManufacturingOrder
    success_url = reverse_lazy('list_mo')
    pk_url_kwarg = 'manufacturingorder_id'
    template_name = 'delete_mo.html'

def MODetailView(request, mo_id):
    mo = get_object_or_404(ManufacturingOrder, id=mo_id)
    #parts = {}
    mos = mo.moproduct_set.all()
    products = {}
    parts = {}
    for m in mos:
        partList = m.product.partamount_set.all()
        #mo_product = MOProduct.objects.get(manufacturing_order=m, product=m.product).values('amount')
        multiplier = m.amount
        for p in partList:
            if parts.get(p.part):
                parts[p.part][0] += (p.amount * multiplier)
            else:
                parts[p.part]= [p.amount * multiplier]
        product_amounts = ProductAmount.objects.filter(from_product=m.product)
        for pr in product_amounts:
            if products.get(pr.to_product):
                products[pr.to_product][0] += (pr.amount * multiplier)
            else:
                products[pr.to_product]= [pr.amount * multiplier]
##        if products:
##            products = products.union(ProductAmount.objects.filter(from_product=m.product))
##        else:
##            products = ProductAmount.objects.filter(from_product=m.product)
    for key, value in parts.items():
        locs = LocationRelationship.objects.filter(part=key)
        amount = 0
        for l in locs:
            amount += l.stock
        needed = value[0] - amount
        if needed <= 0:
            needed = 0
        parts[key].append(needed)
    for key, value in products.items():
        locs = ProductLocation.objects.filter(product=key)
        amount = 0
        for l in locs:
            amount += l.stock
        needed = value[0] - amount
        if needed <= 0:
            needed = 0
        products[key].append(needed)
##    pro_list = products.values_list('from_product', flat=True)
##    print(pro_list)
    return render(request, 'mo_detail.html', {'parts': parts, 'products': products,
                                              'mo': mo})

def print_tokens_digi(request):
    digi = DigiKeyAPI.objects.get(name="DigiKey")
    access = digi.access_token
    refresh = digi.refresh_token
    return render(request, 'print_tokens.html', {'access':access, 'refresh':refresh})

def enter_tokens(request):
    if request.method == 'POST':
        form = EnterTokensForm(request.POST)
        if form.is_valid():
            access = form.cleaned_data['access_token']
            refresh = form.cleaned_data['refresh_token']
            digi = DigiKeyAPI.objects.get(name="DigiKey")
            setattr(digi,"access_token",access)
            setattr(digi,"refresh_token",refresh)
            digi.save()
            return HttpResponseRedirect(reverse('list_types'))
    else:
        form = EnterTokensForm()
    return render(request,'enter_tokens.html',{'form': form})

##def enter_part(request):
##    if request.method == "POST":
##        form = EnterPartForm(request.POST)
##        if form.is_valid():
##            url = form.cleaned_data['url']
##            partType = form.cleaned_data['partType']
##            page = requests.get(url, timeout=10)
##            data = BeautifulSoup(page.text, 'html.parser')
##            manufacturer_table = data.find(id="product-overview")
##            manufacturer_table_list = manufacturer_table.find_all("th")
##            for manufacturer in manufacturer_table_list:
##                header = manufacturer.text.strip()
##                row = manufacturer.find_next_sibling().text.strip()
##                if header == 'Manufacturer':
##                    manu = row
##                if header == 'Manufacturer Part Number':
##                    man_partNumber = row
##                if header == 'Detailed Description':
##                    detailed_descript = row
##
##            manu, created = Manufacturer.objects.get_or_create(name=manu)
##            
##            part_table = data.find(id="product-attribute-table")
##            part_table_list = part_table.find_all("th")
##            part_attr = {}
##            for part in part_table_list:
##                header = part.text.strip()
##                row = part.find_next_sibling().text.strip()
##                part_attr[header] = row
##                
##            part = Part.objects.create(partType=partType, description=detailed_descript)
##            for field in partType.field.all():
##                name = part_attr.get(field.name)
##                if name == 'null' or name is None or name == '-':
##                    name = ''
##                f = field.fields
##                setattr(part, f, name)
##
##            part.save()
##            
##            ManufacturerRelationship.objects.create(part=part, manufacturer=manu,
##                                                partNumber=man_partNumber)
##            redirect_url = reverse('list_parts', args=[partType.pk])
##            return HttpResponseRedirect(redirect_url)
##    else:
##        form = EnterPartForm()
##    return render(request, "enter_part.html", {"form":form})

##def mouser_api(request):
##    if request.method == "POST":
##        form = MouserForm(request.POST)
##        if form.is_valid():
##            partNumber = form.cleaned_data['partNumber']
##            partType = form.cleaned_data['partType']
##            
##            url = 'http://octopart.com/api/v3/parts/match?'
##            url += '&queries=[{"sku":"' + partNumber + '"}]'
##            url += '&apikey=683454dc'
##            url += '&include[]=specs'
##            url += '&include[]=descriptions'
##
##            data = urllib.request.urlopen(url).read()
##            response = json.loads(data)
##
##            fields = Field.objects.filter(typePart=partType)
##            for result in response['results']:
##                description = ''
##                try:
##                    description = result['items'][0]['descriptions'][0]['value']
##                except(IndexError, KeyError):
##                    pass
##                new_part = Part.objects.create(partType=partType, description=description)
##                manufacturer = result['items'][0]['manufacturer']['name']
##                number = result['items'][0]['mpn']
##                manu, created = Manufacturer.objects.get_or_create(name=manufacturer)
##                ManufacturerRelationship.objects.create(part=new_part, manufacturer=manu, partNumber=number)
##                for item in result['items']:
##                    if item['specs']:
##                        for field in fields:
##                            if field.mouser_name:
##                                try:
##                                    value = item['specs'][field.mouser_name]['display_value']
##                                    setattr(new_part, field.fields, value)
##                                except(IndexError, KeyError):
##                                    pass
##                new_part.save()
##            redirect_url = reverse('list_parts', args=[partType.pk])
##            return HttpResponseRedirect(redirect_url)
##    else:
##        form = MouserForm()
##    return render(request, "mouser.html", {'form': form})
##
##def mouser_details(request):
##    response = ''
##    if request.method == "POST":
##        form = MouserForm(request.POST)
##        if form.is_valid():
##            partNumber = form.cleaned_data['partNumber']
##            partType = form.cleaned_data['partType']
##            
##            url = 'http://octopart.com/api/v3/parts/match?'
##            url += '&queries=[{"sku":"' + partNumber + '"}]'
##            url += '&apikey=683454dc'
##            url += '&include[]=specs'
##            url += '&include[]=descriptions'
##
##            data = urllib.request.urlopen(url).read()
##            resp = json.loads(data.decode())
##            res = json.dumps(resp, indent=4)
##            response = []
##            try:
##                respo = resp['results'][0]['items'][0]['specs']
##            except(IndexError, KeyError):
##                respo = {}
##                response.append("No specs can be retrieved")
##            #response = json.dumps(respo, indent=4)
##            
##            for key, value in respo.items():
##                response.append(key)
##            if not response:
##                response.append("No specs can be retrieved")
##    else:
##        form = MouserForm()
##    return render(request, "mouser_detail.html", {'form': form, 'response': response})
