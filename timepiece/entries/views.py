from copy import deepcopy
import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import json

from six.moves.urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView, View
from django.views.generic.edit import FormMixin

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT
#from timepiece.utils.csv import DecimalEncoder
from timepiece.utils.views import cbv_decorator

from timepiece.manager.models import Project, Profile
from timepiece.entries.forms import (
    ClockInForm, ClockOutForm, AddUpdateEntryForm, EntryDashboardForm, ProjectHoursForm,
    ProjectHoursSearchForm, TodoListForm, TodoForm)
from timepiece.entries.models import Entry, ProjectHours, ToDo

class DashboardMixin(object):

    def dispatch(self, request, *args, **kwargs):
        # Since we use get param in multiple places, attach it to the class
        default_week = utils.get_week_start(datetime.date.today()).date()

        if request.method == 'GET':
            week_start_str = request.GET.get('week_start', '')
        else:
            week_start_str = request.POST.get('week_start', '')

        # Account for an empty string
        self.week_start = default_week if week_start_str == '' \
            else utils.get_week_start(datetime.datetime.strptime(
                week_start_str, '%Y-%m-%d').date())

        return super(DashboardMixin, self).dispatch(request, *args, **kwargs)

    def get_hours_for_week(self, week_start=None):
        """
        Gets all ProjectHours entries in the 7-day period beginning on
        week_start.
        """
        week_start = week_start if week_start else self.week_start
        week_end = week_start + relativedelta(days=7)

        return ProjectHours.objects.filter(
            week_start__gte=week_start, week_start__lt=week_end)
    

class Dashboard(DashboardMixin, TemplateView):
    template_name = 'timepiece/dashboard.html'
    #form_class = EntryDashboardForm(self.request.POST, user=self.user, acting_user=self.user)

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        #self.active_tab = active_tab or 'progress'
        self.user = request.user
        
        initial = {'start_time': datetime.datetime.now()}
        form = EntryDashboardForm(self.request.GET, initial=initial, user=self.user, acting_user=self.user)
        return super(Dashboard, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
##        if "entryAdd" in request.POST:
##            if context['form'].is_valid():
##                entry = context['form'].save()
        entry = context['form']
        
       # if "entryNoEnd" in request.POST:
##        updated_data = request.POST.copy()
##        updated_data['end_time'] = None
##        #updated_data.update({'end_time': None})
##        request.POST = updated_data
            #entry = EntryDashboardForm(data=updated_data, user=self.user, acting_user=self.user)
            #entry.end_time= None   
        if entry.is_valid():
            entry.save()
            url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        return super(Dashboard, self).render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        context = super(Dashboard, self).get_context_data(**kwargs)
        week_start = self.week_start
        week_end = week_start + relativedelta(days=7)
        #initial = {'start_time': datetime.datetime.now(), 'end_time': datetime.datetime.now()}
        #initial = {}
        #initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        #form = ProjectHoursSearchForm(initial=initial)
        
        entry = utils.get_active_entry(self.user)
        if(entry == None):
            initial = {'start_time': datetime.datetime.now(),}# 'end_time': datetime.datetime.now()}
        else:
            initial = {'end_time': datetime.datetime.now()}
        form = EntryDashboardForm(self.request.POST or None, instance=entry, initial=initial, user=self.user, acting_user=self.user)

        # Query for the user's active entry if it exists.
        active_entry = utils.get_active_entry(self.user)

        # Process this week's entries to determine assignment progress.
        week_entries = Entry.objects.filter(user=self.user)
        week_entries = week_entries.timespan(week_start, span='week')
        week_entries = week_entries.select_related('project')
        assignments = ProjectHours.objects.filter(
            user=self.user, week_start__gte=week_start, week_start__lt=week_end)
        project_progress = self.process_progress(week_entries, assignments)

        # Total hours that the user is expected to clock this week.
        #total_assigned = self.get_hours_per_week(self.user)
        total_worked = sum([p['worked'] for p in project_progress])

        # Others' active entries.
        others_active_entries = Entry.objects.filter(end_time__isnull=True)
        others_active_entries = others_active_entries.exclude(user=self.user)
        others_active_entries = others_active_entries.select_related('user', 'project')

        project_entries = week_entries.order_by().values(
        'project__name').annotate(sum=Sum('hours')).order_by('-sum')

        todos = ToDo.objects.filter(user=self.user, completed=False)

        context.update({
            #'active_tab': self.active_tab,
            'form': form,
            'active_entry': active_entry,
            'total_worked': total_worked,
            'project_progress': project_progress,
            'week_entries': week_entries,
            'others_active_entries': others_active_entries,
            'week': self.week_start,
            'prev_week': self.week_start - relativedelta(days=7),
            'next_week': self.week_start + relativedelta(days=7),
            'todos': todos,
        })
        return context
    def process_progress(self, entries, assignments):
        """
        Returns a list of progress summary data (pk, name, hours worked, and
        hours assigned) for each project either worked or assigned.
        The list is ordered by project name.
        """
        # Determine all projects either worked or assigned.
        project_q = Q(id__in=assignments.values_list('project__id', flat=True))
        project_q |= Q(id__in=entries.values_list('project__id', flat=True))
        projects = Project.objects.filter(project_q)#.select_related('business')

        # Hours per project.
        project_data = {}
        for project in projects:
            try:
                assigned = assignments.get(project__id=project.pk).hours
            except ProjectHours.DoesNotExist:
                assigned = Decimal('0.00')
            project_data[project.pk] = {
                'project': project,
                'assigned': assigned,
                'worked': Decimal('0.00'),
            }

        for entry in entries:
            pk = entry.project_id
            hours = Decimal('%.5f' % (entry.get_total_seconds() / 3600.0))
            project_data[pk]['worked'] += hours

        # Sort by maximum of worked or assigned hours (highest first).
        key = lambda x: x['project'].name.lower()
        project_progress = sorted(project_data.values(), key=key)

        return project_progress

##def entryForm(request):
##    if request.method == "POST":
##        entry = utils.get_active_entry(request.user)
##        if(entry == None):
##            initial = {'start_time': datetime.datetime.now(), 'end_time': datetime.datetime.now()}
##        else:
##            initial = {'end_time': datetime.datetime.now()}
##        form = EntryDashboardForm(request.POST or None, instance=entry, initial=initial, user=request.user, acting_user=request.user)
##        #form = EntryDashboardForm(request.POST, user=request.user)
##        if form.is_valid():
##            if "entryNoEnd" in request.POST:
##                entry = form.save(commit=False)
##                entry.end_time = None
##                #entry.user = request.user
##                entry.save()
##                return redirect('/')
##            if "entryAdd" in request.POST:
##                entry = form.save(commit=False)
##                #entry.user = request.user
##                entry.save()
##                return redirect('/')
##    else:
##        form = EntryDashboardForm()
##    return redirect(reverse('dashboard')#, "timepiece/dashboard.html", {'form': form})

def to_do(request):
    user = request.user
    todos = ToDo.objects.filter(user=user, completed=False)
    if request.method == "POST":
        if "taskAdd" in request.POST:
            priority = request.POST["priority"]
            description = request.POST["description"]
            Todo = ToDo(priority=priority, description=description, user=user)
            Todo.save()
            return redirect('/')
        if "taskComplete" in request.POST:
            todo_id = request.POST["taskComplete"]            
            todo = ToDo.objects.get(id=int(todo_id))
            todo.completed = True
            todo.save()
            messages.success(request, "Task '{}' has been marked completed".
                             format(todo.description))
            return redirect('/')
          #  return redirect('TodoList')
    return render(request, "timepiece/todo.html", {"todos": todos})

def todo_completed(request):
    user = request.user
    todos = ToDo.objects.filter(completed=True,)
    return render(request, "timepiece/todo-complete.html", {"todos": todos})

def todo_edit(request, todo_id):
    user = request.user
    todo = get_object_or_404(ToDo, id=todo_id)
    if request.method == "POST": 
        form = TodoForm(request.POST, instance=todo)
        if form.is_valid():
            todo = form.save(commit=False)
            todo.user = request.user
            todo.save()
            return redirect('/')
    else:
        form = TodoForm(instance=todo)
    return render(request, "timepiece/todo-edit.html", {'form': form})

def todo_admin_create(request):
    data = request.POST or None
    form = TodoListForm(data)
    if form.is_valid():
        todo = form.save()
        messages.success(request, "'{}' has been added for '{}'".
                        format(todo.description, todo.user))
    return render(request, "timepiece/todo-create.html", {'form': form})

def todo_admin_edit(request, todo_id):
    todo = get_object_or_404(ToDo, id=todo_id)
    if request.method == "POST": 
        form = TodoListForm(request.POST, instance=todo)
        if form.is_valid():
            form.save()
            return redirect('todo_list')
    else:
        form = TodoListForm(instance=todo)
    return render(request, "timepiece/todo-edit.html", {'form': form})


class TodoAdminListView(ListView):
    queryset = ToDo.objects.filter(completed=False)
    template_name = "timepiece/todo-list.html"


class TodoCompletedListView(ListView):
    queryset = ToDo.objects.filter(completed=True)
    template_name = "timepiece/todo-complete-all.html"

@permission_required('entries.can_clock_in')
@transaction.atomic
def clock_in(request):
    """For clocking the user into a project."""
    user = request.user
    # Lock the active entry for the duration of this transaction, to prevent
    # creating multiple active entries.
    active_entry = utils.get_active_entry(user, select_for_update=True)

    initial = dict([(k, v) for k, v in request.GET.items()])
    data = request.POST or None
    form = ClockInForm(data, initial=initial, user=user, active=active_entry)
    if form.is_valid():
        entry = form.save()
        message = 'You have clocked into {0}.'.format(
             entry.project)
        messages.info(request, message)
        return HttpResponseRedirect(reverse('dashboard'))

    return render(request, 'timepiece/entry/clock_in.html', {
        'form': form,
        'active': active_entry,
    })


@permission_required('entries.can_clock_out')
def clock_out(request):
    entry = utils.get_active_entry(request.user)
    if not entry:
        message = "Not clocked in"
        messages.info(request, message)
        return HttpResponseRedirect(reverse('dashboard'))
    if request.POST:
        form = ClockOutForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            message = 'You have clocked out of {0}.'.format(
                entry.project)
            messages.info(request, message)
            return HttpResponseRedirect(reverse('dashboard'))
        else:
            message = 'Please correct the errors below.'
            messages.error(request, message)
    else:
        form = ClockOutForm(instance=entry)
    return render(request, 'timepiece/entry/clock_out.html', {
        'form': form,
        'entry': entry,
    })


@permission_required('entries.change_entry')
def create_edit_entry(request, entry_id=None):
    if entry_id:
        try:
            entry = Entry.no_join.get(pk=entry_id)
        except Entry.DoesNotExist:
            entry = None
        else:
            if not (entry.is_editable or request.user.has_perm('entries.view_payroll_summary')):
                raise Http404
    else:
        entry = None

    entry_user = entry.user if entry else request.user

    if request.method == 'POST':
        form = AddUpdateEntryForm(data=request.POST,
                                  instance=entry,
                                  user=entry_user,
                                  acting_user=request.user)
        if form.is_valid():
            entry = form.save()
            if entry_id:
                message = 'The entry has been updated successfully.'
            else:
                message = 'The entry has been created successfully.'
            messages.info(request, message)
            url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        else:
            message = 'Please fix the errors below.'
            messages.error(request, message)
    else:
        initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        form = AddUpdateEntryForm(instance=entry,
                                  user=entry_user,
                                  initial=initial,
                                  acting_user=request.user)

    return render(request, 'timepiece/entry/create_edit.html', {
        'form': form,
        'entry': entry,
    })

@permission_required('entries.can_delete_entry')
def delete_entry(request, entry_id):
    """
    Give the user the ability to delete a log entry, with a confirmation
    beforehand.  If this method is invoked via a GET request, a form asking
    for a confirmation of intent will be presented to the user. If this method
    is invoked via a POST request, the entry will be deleted.
    """
    try:
        entry = Entry.no_join.get(pk=entry_id, user=request.user)
    except Entry.DoesNotExist:
        message = 'No such entry found.'
        messages.info(request, message)
        url = request.GET.get('next', reverse('dashboard'))
        return HttpResponseRedirect(url)

    if request.method == 'POST':
        key = request.POST.get('key', None)
        if key and key == entry.delete_key:
            entry.delete()
            message = 'Deleted {0}.'.format(entry.project)
            messages.info(request, message)
            url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        else:
            message = 'You are not authorized to delete this entry!'
            messages.error(request, message)

    return render(request, 'timepiece/entry/delete.html', {
        'entry': entry,
    })

