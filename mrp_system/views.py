from django.shortcuts import render, get_object_or_404, redirect
from django.http import (HttpResponse, HttpResponseRedirect, HttpResponseNotFound,
                         JsonResponse)
from django.views.generic import ListView, TemplateView
from mrp_system.models import (Part, Type, Field, Manufacturer,
                               ManufacturerRelationship, Location,
                               LocationRelationship, DigiKeyAPI,
                               PartAmount, Product, ProductAmount, ManufacturingOrder,
                               MOProduct, ProductLocation)
from mrp_system.forms import (FilterForm, PartForm, LocationForm, LocationFormSet,
                              MergeLocationsForm, ManufacturerForm, ManufacturerFormSet,
                              MergeManufacturersForm, FieldFormSet, TypeForm, APIForm,
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

def view_file(request, name):
    storage = DefaultStorage()
    f = storage.open(part.document.name, mode='rb')

class TypeListView(ListView):
    model = Type
    template_name = 'type_list.html'
    ordering = ['name']

class ManufacturerListView(ListView):
    model = Manufacturer
    template_name = 'manufacturer_list.html'
    ordering = ['name']

class LocationListView(ListView):
    model = Location
    template_name = 'location_list.html'
    ordering = ['name']
    

def PartCreate(request, type_id):
    partType = Type.objects.get(id=type_id)

    if request.method == 'POST':
        form = PartForm(type_id, request.POST, request.FILES)
        part_formset = ManufacturerFormSet(request.POST)
        location_formset = LocationFormSet(request.POST)
        if form.is_valid() and part_formset.is_valid() and location_formset.is_valid():
            self_object = form.save(commit=False)
            self_object.partType_id = type_id
            self_object.save()
            location_formset.instance = self_object
            location_formset.save()
            part_formset.instance = self_object
            part_formset.save()
            url = reverse('list_parts', args=[partType.pk])
            return HttpResponseRedirect(url)
    else:
        form = PartForm(type_id=type_id)
        part_formset = ManufacturerFormSet()
        location_formset = LocationFormSet()
    return render(request,'part_form.html',{'part_form': form,
                                            'location_formset': location_formset,
                                            'part_formset': part_formset,
                                            'partType': partType})

def PartEdit(request, type_id, id):
    partType = Type.objects.get(id=type_id)
    instance = get_object_or_404(Part, id=id)

    if request.method == 'POST':
        #self.object = None
        form = PartForm(type_id, request.POST, request.FILES, instance=instance)
        part_formset = ManufacturerFormSet(request.POST, instance=instance)
        location_formset = LocationFormSet(request.POST, instance=instance)
        if form.is_valid(): # and part_formset.is_valid()):
            part = form.save(commit=False)
            part.partType_id = type_id
            if part_formset.is_valid() and location_formset.is_valid():
                part.save()
                part_formset.save()
                location_formset.save()
                url = reverse('list_parts', args=[partType.pk])
                return HttpResponseRedirect(url)
    else:
        #self.object = None
        form = PartForm(type_id=type_id, instance=instance)
        part_formset = ManufacturerFormSet(instance=instance)
        location_formset = LocationFormSet(instance=instance)
    return render(request,'part_form.html',{'part_form': form,
                                            'location_formset': location_formset,
                                            'part_formset': part_formset,
                                            'partType': partType})

def quick_type_create(request):
    if request.method == 'POST':
        form = QuickTypeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['fields']
            data = data.split(",")
            print(data)
            typeName = data.pop(0).strip()
            suffix = data.pop(0).strip()
            print(typeName + ": " + suffix)
            fields = {}
            number = 1
            for d in data:
                fields[d.strip()] = "char"+str(number)
                number += 1
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
##        return self.render_to_response(
##            self.get_context_data(form=form, field_formset=field_formset))

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
        for f in forms:
            f.fields = 'char' + str(count)
            count += 1
            f.save()
        #field_formset.save()
        return super(TypeCreate, self).form_valid(form)

    def form_invalid(self, form, field_formset):
        #return super().form_invalid(form, field_formset)
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
        field_formset.instance = self.object
##        forms = field_formset.save(commit=False)
##        count = 1
##        for f in forms:
##            f.prefix
##            f.fields = 'char' + str(count)
##            count += 1
##            f.save()
##        #field_forms
        field_formset.save()
        return HttpResponseRedirect(self.get_success_url())

       # return super(TypeEdit, self).form_valid(form)

    def form_invalid(self, form, field_formset):
        return self.render_to_response(
            self.get_context_data(form=form, field_formset=field_formset))

class DeleteType(DeleteView):
    model = Type
    success_url = reverse_lazy('list_types')
    pk_url_kwarg = 'type_id'
    template_name = 'delete_type.html'

def ListParts(request, type_id):
    filters={}
    partType = Type.objects.get(id=type_id)
    parts = Part.objects.filter(partType=partType)
    fields = Field.objects.filter(typePart_id=type_id)
    name = ''
    for field in fields:
        if field.fields == "char1":
            name = field.name
    #typeName = partType.name
    searchField = None
    models={}
    for field in fields:
        models[field.fields] = field.name
    if request.method == 'POST':
        form = FilterForm(request.POST, models=models, type_id=type_id)
        manufacturer = request.POST.getlist('manufacturer')
        location = request.POST.getlist('location')
        char1 = request.POST.getlist('char1')
        char2 = request.POST.getlist('char2')
        char3 = request.POST.getlist('char3')
        char4 = request.POST.getlist('char4')
        char5 = request.POST.getlist('char5')
        char6 = request.POST.getlist('char6')
        char7 = request.POST.getlist('char7')
        char8 = request.POST.getlist('char8')
        char9 = request.POST.getlist('char9')
        char10 = request.POST.getlist('char10')
        char11 = request.POST.getlist('char11')
        char12 = request.POST.getlist('char12')
        char13 = request.POST.getlist('char13')
        char14 = request.POST.getlist('char14')
        char15 = request.POST.getlist('char15')
        char16 = request.POST.getlist('char16')
        char17 = request.POST.getlist('char17')
        char18 = request.POST.getlist('char18')
        char19 = request.POST.getlist('char19')
        char20 = request.POST.getlist('char20')
        char21 = request.POST.getlist('char21')
        char22 = request.POST.getlist('char22')
        char23 = request.POST.getlist('char23')
        char24 = request.POST.getlist('char24')
        char25 = request.POST.getlist('char25')
        char26 = request.POST.getlist('char26')
        char27 = request.POST.getlist('char27')
        char28 = request.POST.getlist('char28')
        char29 = request.POST.getlist('char29')
        char30 = request.POST.getlist('char30')
        char31 = request.POST.getlist('char31')
        char32 = request.POST.getlist('char32')
        char33 = request.POST.getlist('char33')
        char34 = request.POST.getlist('char34')
        char35 = request.POST.getlist('char35')
        searchField = request.POST.get('search')
        if len(manufacturer) > 0:
            filters['manufacturer__in'] = manufacturer
        if len(location) > 0:
            filters['location__in'] = location
        if len(char1) > 0:
            filters['char1__in'] = char1
        if len(char2) > 0:
            filters['char2__in'] = char2
        if len(char3) > 0:
            filters['char3__in'] = char3
        if len(char4) > 0:
            filters['char4__in'] = char4
        if len(char5) > 0:
            filters['char5__in'] = char5
        if len(char6) > 0:
            filters['char6__in'] = char6
        if len(char7) > 0:
            filters['char7__in'] = char7
        if len(char8) > 0:
            filters['char8__in'] = char8
        if len(char9) > 0:
            filters['char9__in'] = char9
        if len(char10) > 0:
            filters['char10__in'] = char10
        if len(char11) > 0:
            filters['char11__in'] = char11
        if len(char12) > 0:
            filters['char12__in'] = char12
        if len(char13) > 0:
            filters['char13__in'] = char13
        if len(char14) > 0:
            filters['char14__in'] = char14
        if len(char15) > 0:
            filters['char15__in'] = char15
        if len(char16) > 0:
            filters['char16__in'] = char16
        if len(char17) > 0:
            filters['char17__in'] = char17
        if len(char18) > 0:
            filters['char18__in'] = char18
        if len(char19) > 0:
            filters['char19__in'] = char19
        if len(char20) > 0:
            filters['char20__in'] = char20
        if len(char21) > 0:
            filters['char21__in'] = char21
        if len(char22) > 0:
            filters['char22__in'] = char22
        if len(char23) > 0:
            filters['char23__in'] = char23
        if len(char24) > 0:
            filters['char24__in'] = char24
        if len(char25) > 0:
            filters['char25__in'] = char25
        if len(char26) > 0:
            filters['char26__in'] = char26
        if len(char27) > 0:
            filters['char27__in'] = char27
        if len(char28) > 0:
            filters['char28__in'] = char28
        if len(char29) > 0:
            filters['char29__in'] = char29
        if len(char30) > 0:
            filters['char30__in'] = char30
        if len(char31) > 0:
            filters['char31__in'] = char31
        if len(char32) > 0:
            filters['char32__in'] = char32
        if len(char33) > 0:
            filters['char33__in'] = char33
        if len(char34) > 0:
            filters['char34__in'] = char34
        if len(char35) > 0:
            filters['char35__in'] = char35
        form=FilterForm(models=models, type_id=type_id)
    else:
        form = FilterForm(models=models, type_id=type_id)
    parts = parts.filter(**filters)
    string_filters = 'Current Filters: '
    for key, value in filters.items():
        if key == 'location__in':
            locations = Location.objects.filter(id__in=value)
            string_filters += ", ".join(l.name for l in locations) + '; '
        elif key == 'manufacturer__in':
            manufacturers = Manufacturer.objects.filter(id__in=value)
            string_filters += ", ".join(m.name for m in manufacturers) + '; '
        else:
            string_filters += ", ".join(v for v in value) + '; '
    if searchField == "" or searchField is None:
        parts = parts.distinct('id')
    else:
        parts = parts.annotate(search=SearchVector('manufacturer__name', 'location__name', 'description',
                                                   'enigmusingPartNumber', 'manufacturerrelationship__partNumber',
                                                   'char1', 'char2')).filter(search=searchField)
        parts = parts.distinct('id')
    current_filters = ''
    if filters.items():
        for k, v in filters.items():
            current_filters += "{},   ".format(v)
    return render(request, 'part_list.html', {'type': partType, 'parts': parts,
                                              'fields': fields, 'form': form,
                                              'name': name, 'string_filters': string_filters})
    

class CreateManufacturer(CreateView):
    model = Manufacturer
    fields = ['name']
    template_name = 'manufacturer_form.html'
    success_url = reverse_lazy('list_manufacturers')

    def get_context_data(self, **kwargs):
        kwargs['manufacturers'] = Manufacturer.objects.order_by('name')
        return super(CreateManufacturer, self).get_context_data(**kwargs)

class CreateLocation(CreateView):
    model = Location
    fields = ['name']
    template_name = 'location_form.html'
    success_url = reverse_lazy('list_locations')

    def get_context_data(self, **kwargs):
        kwargs['locations'] = Location.objects.order_by('name')
        return super(CreateLocation, self).get_context_data(**kwargs)

class ManufacturerUpdate(UpdateView):
    model = Manufacturer
    fields = ['name']
    pk_url_kwarg = 'manufacturer_id'
    template_name = 'update_manufacturer.html'
    success_url = reverse_lazy('list_manufacturers')

class LocationUpdate(UpdateView):
    model = Location
    fields = ['name']
    pk_url_kwarg = 'location_id'
    template_name = 'update_location.html'
    success_url = reverse_lazy('list_locations')

def LocationRelationshipEdit(request, locationrelationship_id):
    rel = get_object_or_404(LocationRelationship, id=locationrelationship_id)
    if request.method == "POST":
        form = LocationForm(request.POST, instance=rel)
        if form.is_valid():
            form.save()
            nextUrl = request.POST.get('next', '/')
            return HttpResponseRedirect(nextUrl)
    else:
        form = LocationForm(instance=rel)
    return render(request, 'update_loc_relationship.html', {'form': form})

def LocationRelationshipAdd(request, part_id):
    part = get_object_or_404(Part, id=part_id)
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
    return render(request, 'add_loc_relationship.html', {'form': form})

class ManufacturerDelete(DeleteView):
    model = Manufacturer
    pk_url_kwarg = 'manufacturer_id'
    template_name = 'delete_manufacturer.html'
    success_url = reverse_lazy('list_manufacturers')

class DeletePart(DeleteView):
    model = Part
    success_url = reverse_lazy('list_types')
    pk_url_kwarg = 'part_id'
    template_name = 'delete_part.html'

class LocationDelete(DeleteView):
    model = Location
    pk_url_kwarg = 'location_id'
    template_name = 'delete_location.html'
    success_url = reverse_lazy('list_locations')

def MergeManufacturerView(request):
    if request.method == "POST":
        form = MergeManufacturersForm(request.POST)
        if form.is_valid():
            primary_object = form.cleaned_data['primary']
            alias_object = form.cleaned_data['alias']
            MergeManufacturer(primary_object, alias_object)
            return redirect('list_manufacturers')
    else: form = MergeManufacturersForm()
    return render(request, "merge_manufacturers.html", {"form":form})

def MergeManufacturer(primary_object, alias_object):
    if not isinstance(alias_object, Manufacturer):
        raise TypeError('Only Manufacturer instances can be merged')
    
    if not isinstance(primary_object, Manufacturer):
        raise TypeError('Only Manufacturer instances can be merged')

    parts = alias_object.part_set.all()
    partNumber = []
    partSet = []
    for part in parts:
        m = ManufacturerRelationship.objects.get(part=part, manufacturer=alias_object)
        partNumber.append(m.partNumber)
        partSet.append(m.part)
    alias_object.part_set.clear()
    length = len(partSet)
    for x in range(length):
        ManufacturerRelationship.objects.create(part=partSet[x],
                                                manufacturer=primary_object,
                                                partNumber=partNumber[x])
    alias_object.delete()

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
    parts = alias_object.part_set.all()
    for part in parts:
        part.location.add(primary_object)
        part.location.filter(id=alias_object.id).delete()


import http.client

def enter_digi_part(request):
    if request.method == "POST":
        form = APIForm(request.POST)
        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            partNumber = form.cleaned_data['partNumber']
            manuPartNumb = form.cleaned_data['manuPartNumber']
            website = form.cleaned_data['website']
            digi = DigiKeyAPI.objects.get(name="DigiKey")

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

            accessToken = response['access_token']
            setattr(digi,"refresh_token",refreshToken)
            setattr(digi,"access_token",accessToken)
            digi.save()
            if website == 'Digi-Key' and barcode:
            #partNumber = 'H10247-ND'
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

            elif website == 'Mouser' and barcode:
                search = barcode
                
            elif partNumber:
                search = partNumber
            elif manuPartNumb:
                search = manuPartNumb
                
            else:
                return HttpResponseNotFound('<h1>Must select a website and enter a field!</h1>')

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
            f = open("data4.txt", "a")
            f.write(string)
            if website == 'Digi-Key':
                try:
                    part = jstr['ExactDigiKeyPart']
                    data = part['Parameters']
                except(IndexError, KeyError, TypeError):
                    try:
                        part=jstr['ExactParts'][0]
                        data = part['Parameters']
                    except(IndexError, KeyError, TypeError):
                        return HttpResponseNotFound('<h1>Invalid Part Number</h1>')
            elif website == 'Mouser':
                try:
                    part = jstr['ExactParts'][0]
                    data = part['Parameters']
                except(IndexError, KeyError, TypeError):
                    return HttpResponseNotFound('<h1>Invalid Part Number</h1>')
            else:
                return HttpResponseNotFound('<h1>Must select a website</h1>')
            params = {}
            for value in data:
                params[value['Parameter']] = value['Value']
            f.write("-----------------------")
            for key, value in params.items():
                f.write(key)
            typeName = part['Family']['Text']
            f.write("$$$$" + typeName)
            f.write("!!!!!!!!!")
            f.write(json.dumps(params))
            list_name = re.findall(r'\w+', typeName)
            word_count = len(list_name)
            prefix = ""
            if word_count == 1:
                prefix = typeName[:3].upper()
            if word_count == 2:
                prefix = (list_name[0][:1] + list_name[1][:2]).upper()
            if word_count >= 3:
                prefix = (list_name[0][:1] + list_name[1][:1] + list_name[2][:1]).upper()
            partType, created = Type.objects.get_or_create(name=typeName)
            count = 1
            #print(params)
            if created:
                setattr(partType,"prefix",prefix)
                partType.save()
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
                manu, created = Manufacturer.objects.get_or_create(name=manufacturer)
                exists = ManufacturerRelationship.objects.filter(manufacturer=manu, partNumber=number)
                if exists:
                    messages.warning(request, ('Manufacturer Part Number already exists.'))
                    url = reverse('digi_part')
                    return HttpResponseRedirect(url)
                #return HttpResponseNotFound('<h1>Part already exists!</h1> <a href="{% url \'list_product\' %}">Products</a>')
            new_part = Part.objects.create(partType=partType, description=description)
            if manufacturer:
                ManufacturerRelationship.objects.create(part=new_part, manufacturer=manu, partNumber=number)
            try:
                datasheet_url = part['PrimaryDatasheet']
                if 'pdf' in datasheet_url:
                    try:
                        datasheet_name = urlparse(datasheet_url).path.split('/')[-1]
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'}
                        response = requests.get(datasheet_url, headers=headers)
                        if response.status_code == 200:
                            new_part.datasheet.save(datasheet_name, ContentFile(response.content), save=True)
                    except (requests.exceptions.SSLError):
                        try:
                            datasheet_name = urlparse(datasheet_url).path.split('/')[-1]
                            headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:35.0) Gecko/20100101 Firefox/35.0'}
                            response = requests.get(datasheet_url, headers=headers)
                            if response.status_code == 200:
                                new_part.datasheet.save(datasheet_name, ContentFile(response.content), save=True)
                        except (requests.exceptions.SSLError):
                            pass
            except(IndexError, KeyError, TypeError):
                pass
            for field in fields:
                name = field.name
                field_name = field.fields
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
            redirect_url = reverse('edit_part', args=[partType.pk, new_part.id])
            return HttpResponseRedirect(redirect_url)
    else:
        form = APIForm()
    return render(request, "oauth.html", {'form': form})


def get_parts(request):
    searchField = request.GET.get('search')
    parts = Part.objects.annotate(search=SearchVector('partType__name', 'description', 'location__name',
                                                      'engimusingPartNumber', 'manufacturer__name',
                                                      'manufacturerrelationship__partNumber'),).filter(search=searchField)
    parts_dict = {}
    for part in parts:
        parts_dict[part.id] = part.description
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

class ProductCreate(CreateView):
    form_class = ProductForm
    template_name = 'timepiece/project/createproject.html'
    success_url = reverse_lazy('list_projects')

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        part_formset = PartToProductFormSet()
        product_formset = ProductToProductFormSet()
        location_formset = ProductLocationFormSet()
        return self.render_to_response(
            self.get_context_data(form=form, part_formset=part_formset, product_formset=product_formset,
                                  location_formset=location_formset))

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        part_formset = PartToProductFormSet(request.POST)
        product_formset = ProductToProductFormSet(request.POST)
        location_formset = ProductLocationFormSet(request.POST)
        if (form.is_valid() and part_formset.is_valid() and
            product_formset.is_valid() and location_formset.is_valid()):
            return self.form_valid(form, part_formset, product_formset, location_formset)
        else:
            return self.form_invalid(form, part_formset, product_formset, location_formset)

    def form_valid(self, form, part_formset, product_formset, location_formset):
        self.object = form.save()
        part_formset.instance = self.object
        part_formset.save()
        product_formset.instance = self.object
        product_formset.save()
        location_formset.instance = self.object
        location_formset.save()
        return super(ProductCreate, self).form_valid(form)

    def form_invalid(self, form, part_formset, product_formset, location_formset):
        return self.render_to_response(
            self.get_context_data(form=form,part_formset=part_formset, product_formset=product_formset,
                                  location_formset=location_formset))


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
            for pa in partList2:
                if parts.get(pa.part):
                    parts[pa.part]+=pa.amount
                else:
                    parts[pa.part]=pa.amount
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
