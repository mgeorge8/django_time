from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import ListView, TemplateView
from mrp_system.models import (Part, Type, Field, Manufacturer,
                               ManufacturerRelationship, Location, LocationRelationship)
from mrp_system.forms import (FilterForm, PartForm, LocationForm, LocationFormSet, MergeLocationsForm, ManufacturerForm,
ManufacturerFormSet, MergeManufacturersForm, FieldFormSet, TypeForm, TypeSelectForm, EnterPartForm)
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.forms.models import inlineformset_factory
from django.urls import reverse, reverse_lazy
from django.forms import ModelForm
from django import forms
from django.db.models.functions import Cast
from django.db.models import CharField
from django.contrib.postgres.search import SearchVector
from django.core.files.storage import DefaultStorage
import requests
from bs4 import BeautifulSoup

def view_file(request, name):
    storage = DefaultStorage()
    f = storage.open(part.document.name, mode='rb')

class TypeListView(ListView):
    model = Type
    template_name = 'type_list.html'

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

class TypeCreate(CreateView):
    form_class = TypeForm
    template_name = 'type_form.html'
    success_url = reverse_lazy('list_types')

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        field_formset = FieldFormSet()
        return self.render_to_response(
            self.get_context_data(form=form, field_formset=field_formset))

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
        field_formset.save()
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
        field_formset = FieldFormSet(instance=self.object)
        return self.render_to_response(
            self.get_context_data(form=form, field_formset=field_formset))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        field_formset = FieldFormSet(request.POST, instance=self.object)
        if (form.is_valid() and field_formset.is_valid()):
            return self.form_valid(form, field_formset)
        else:
            return self.form_invalid(form, field_formset)

    def form_valid(self, form, field_formset):
        self.object = form.save()
        field_formset.instance = self.object
        field_formset.save()
        return HttpResponseRedirect(self.get_success_url())

       # return super(TypeEdit, self).form_valid(form)

    def form_invalid(self, form, field_formset):
        return self.render_to_response(
            self.get_context_data(form=form, field_formset=field_formset))



def ListParts(request, type_id):
    filters={}
    partType = Type.objects.get(id=type_id)
    parts = Part.objects.filter(partType=partType)
    fields = Field.objects.filter(typePart_id=type_id)
    name = ''
    for field in fields:
        if field.fields == "char1":
            name = field.name
    typeName = partType.name
    searchField = None
    models={}
    for field in fields:
        models[field.fields] = field.name
    if request.method == 'POST':
        form = FilterForm(request.POST, models=models, typeName=typeName)
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
        integer1 = request.POST.getlist('integer1')
        integer2 = request.POST.getlist('integer2')
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
            filters['char16__in'] = char15
        if len(char17) > 0:
            filters['char17__in'] = char15
        if len(char18) > 0:
            filters['char18__in'] = char15
        if len(char19) > 0:
            filters['char19__in'] = char15
        if len(char20) > 0:
            filters['char20__in'] = char15
        if len(integer1) > 0:
            filters['integer1__in'] = integer1
        if len(integer2) > 0:
            filters['integer2__in'] = integer2
        form=FilterForm(models=models, typeName=typeName)
    else:
        form = FilterForm(models=models, typeName=typeName)
    parts = parts.filter(**filters)
    if searchField == "" or searchField is None:
        parts = parts.distinct('id')
    else:
        parts = parts.annotate(search=SearchVector('manufacturer__name', 'location__name', 'char1', 'char2', Cast('integer1', CharField()), Cast('integer2', CharField()))).filter(search=searchField)
        parts = parts.distinct('id')
    current_filters = ''
    if filters.items():
        for k, v in filters.items():
            current_filters += "{},   ".format(v)
    return render(request, 'part_list.html', {'type': partType, 'parts': parts,
                                              'fields': fields, 'form': form,
                                              'name': name})
    

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
            print(nextUrl)
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

def enter_part(request):
    if request.method == "POST":
        form = EnterPartForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            partType = form.cleaned_data['partType']
            page = requests.get(url, timeout=10)
            data = BeautifulSoup(page.text, 'html.parser')
            manufacturer_table = data.find(id="product-overview")
            manufacturer_table_list = manufacturer_table.find_all("th")
            for manufacturer in manufacturer_table_list:
                header = manufacturer.text.strip()
                row = manufacturer.find_next_sibling().text.strip()
                if header == 'Manufacturer':
                    manu = row
                if header == 'Manufacturer Part Number':
                    man_partNumber = row
                if header == 'Detailed Description':
                    detailed_descript = row

            manu, created = Manufacturer.objects.get_or_create(name=manu)
            
            part_table = data.find(id="product-attribute-table")
            part_table_list = part_table.find_all("th")
            part_attr = {}
            for part in part_table_list:
                header = part.text.strip()
                row = part.find_next_sibling().text.strip()
                part_attr[header] = row
                
            part = Part.objects.create(partType=partType, description=detailed_descript)
            for field in partType.field.all():
                name = part_attr.get(field.name)
                f = field.fields
                setattr(part, f, name)

            part.save()
            
            ManufacturerRelationship.objects.create(part=part, manufacturer=manu,
                                                partNumber=man_partNumber)
            redirect_url = reverse('list_parts', args=[partType.pk])
            return HttpResponseRedirect(redirect_url)
    else:
        form = EnterPartForm()
    return render(request, "enter_part.html", {"form":form})

import http.client

def oauth(request):

    conn = http.client.HTTPSConnection("api.digikey.com")

    payload = "{\"SearchOptions\":[\"ManufacturerPartSearch\"],\"Keywords\":\"p5555-nd\",\"RecordCount\":\"10\",\"RecordStartPosition\":\"0\",\"Filters\":{\"CategoryIds\":[27442628],\"FamilyIds\":[81316194],\"ManufacturerIds\":[88520800],\"ParametricFilters\":[{\"ParameterId\":\"725\",\"ValueId\":\"7\"}]},\"Sort\":{\"Option\":\"SortByUnitPrice\",\"Direction\":\"Ascending\",\"SortParameterId\":\"50\"},\"RequestedQuantity\":\"50\"}"

    headers = {
        'x-ibm-client-id': '73432ca9-e8ba-4965-af17-a22107f63b35',
        'x-digikey-locale-site': "US",
        'x-digikey-locale-language': "en",
        'x-digikey-locale-currency': "USD",
        #'x-digikey-locale-shiptocountry': ,
##        'x-digikey-customer-id': "REPLACE_THIS_VALUE",
##        'x-digikey-partner-id': "REPLACE_THIS_VALUE",
        'authorization': "QVhAum4tdogouAdEkCt23amqaMad",
        'content-type': "application/json",
        'accept': "application/json"
        }

    conn.request("POST", "/services/partsearch/v2/keywordsearch", payload, headers)

    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))
    return render(request, "oauth.html", {'code':data})




