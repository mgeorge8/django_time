import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Permission
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView

from timepiece import utils

from timepiece.manager.models import Project, Profile
from timepiece.entries.forms import (ClockInForm, ClockOutForm,
                                     AddUpdateEntryForm, EntryDashboardForm,
                                     TodoAdminForm, TodoForm)
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

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        #set start time field value on load/refresh
        initial = {'start_time': datetime.datetime.now()}
        form = EntryDashboardForm(self.request.GET, initial=initial, user=self.user, acting_user=self.user)
        return super(Dashboard, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        entry = context['form']
        #for the add entry clock in form on home page
        if entry.is_valid():
            entry.save()
            #redirect to same page with entry added
            url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        return super(Dashboard, self).render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        context = super(Dashboard, self).get_context_data(**kwargs)
        week_start = self.week_start
        week_end = week_start + relativedelta(days=7)
    
        entry = utils.get_active_entry(self.user)
        if(entry == None):
            initial = {'start_time': datetime.datetime.now(),}
        else:
            initial = None
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
        total_worked = sum([p['worked'] for p in project_progress])

        project_entries = week_entries.order_by().values(
        'project__name').annotate(sum=Sum('hours')).order_by('-sum')

        todos = ToDo.objects.filter(user=self.user, completed=False)

        context.update({
            'form': form,
            'active_entry': active_entry,
            'total_worked': total_worked,
            'project_progress': project_progress,
            'week_entries': week_entries,
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
            #get end_time from form
            end = form.cleaned_data.get('end_time')
            #get all other fields from active entry
            entry_user = entry.user
            start = entry.start_time
            project = entry.project
            activities = entry.activities
            start_date = start.date()
            end_date = end.date()
            delta = end_date - start_date
            #start and end dates are the same
            if delta.days == 0:
                entry=form.save()
            #if end date is one day after start date, split up for 2 entries
            elif delta.days == 1:
                #make end be the end of start time day
                end_of_day = start.replace(hour=23, minute=59, second=59, microsecond=999999)
                entry.end_time = end_of_day
                entry.save()
                #start of second entry is one microsecond after end of 1st entry
                start_of_next_day = end_of_day + datetime.timedelta(microseconds=1)
                entry2 = Entry(user=entry_user, project=project,start_time=start_of_next_day,
                               end_time=end,activities=activities)
                entry2.save()
            #end date is before start date or more than one day apart
            else:
                message = 'Dates can only be one day apart at most.'
                messages.warning(request, message)
                return HttpResponseRedirect(reverse('clock_out'))
            message = 'You have clocked out of {0}.'.format(
                entry.project)
            messages.info(request, message)
            return HttpResponseRedirect(reverse('dashboard'))
        else:
            message = 'Please correct the errors below.'
            messages.warning(request, message)
    else:
        form = ClockOutForm(instance=entry)
    return render(request, 'timepiece/entry/clock_out.html', {
        'form': form,
        'entry': entry,
    })


@permission_required('entries.change_entry')
def create_edit_entry(request, entry_id=None):
    #get current entry if editing
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
            start = form.cleaned_data.get("start_time")
            project = form.cleaned_data.get("project")
            activities = form.cleaned_data.get("activities")
            end = form.cleaned_data.get("end_time")
            #make sure not editing active entry and there's an end time
            if end:
                start_date = start.date()
                end_date = end.date()
                #time between
                delta = end_date - start_date

                #start and end dates are the same
                if delta.days == 0:
                    entry=form.save()
                #if end date is after start date (next day)
                elif delta.days == 1:
                    end_of_day = start.replace(hour=23, minute=59, second=59, microsecond=999999)
                    #if editing entry, update all fields from form
                    if entry_id:
                        entry.end_time = end_of_day
                        entry.project = project
                        entry.activities
                        entry.start_time=start
                        entry.save()
                    else:
                        entry1 = Entry(user=entry_user,project=project,start_time=start,
                                   end_time=end_of_day,activities=activities)
                        entry1.save()
                    start_of_next_day = end_of_day + datetime.timedelta(microseconds=1)
                    entry2 = Entry(user=entry_user, project=project,start_time=start_of_next_day,
                                   end_time=end,activities=activities)
                    entry2.save()
                else:
                    message = 'Dates can only be one day apart at most.'
                    messages.warning(request, message)
                    return render(request, 'timepiece/entry/create_edit.html', {
                            'form': form,
                            'entry': entry,
                            })
            else:
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
            messages.warning(request, message)
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
            messages.warning(request, message)

    return render(request, 'timepiece/entry/delete.html', {
        'entry': entry,
    })

#used to process todo's on home page
def to_do(request):
    user = request.user
    todos = ToDo.objects.filter(user=user, completed=False)
    if request.method == "POST":
        #the different buttons in todo section have names to direct to correct action
        if "taskAdd" in request.POST:
            priority = request.POST["priority"]
            description = request.POST["description"]
            Todo = ToDo(priority=priority, description=description, user=user)
            Todo.save()
            messages.success(request, "Task '{}' has been added.".
                        format(Todo.description))
            return redirect('/')
        if "taskComplete" in request.POST:
            #taskComplete is value assigned to button
            todo_id = request.POST["taskComplete"]            
            todo = ToDo.objects.get(id=int(todo_id))
            todo.completed = True
            todo.save()
            messages.success(request, "Task '{}' has been marked completed".
                             format(todo.description))
            return redirect('/')
        if "taskDelete" in request.POST:
            todo_id = request.POST["taskDelete"]
            todo = ToDo.objects.get(id=int(todo_id))
            todo.delete()
            messages.success(request, "Task '{}' has been deleted.".
                        format(todo.description))
            return redirect('/')
    return render(request, "timepiece/todo/todo.html", {"todos": todos})

#user can view their todo's that have been marked completed
def todo_completed(request):
    user = request.user
    todos = ToDo.objects.filter(completed=True,)
    return render(request, "timepiece/todo/todo-complete.html", {"todos": todos})

#user can edit their todo's
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
    return render(request, "timepiece/todo/todo-edit.html", {'form': form})

#works for user or admin
def todo_delete(request, todo_id):
    todo = get_object_or_404(ToDo, id=todo_id)
    todo.delete()
    #get previous url
    return redirect('/')

#separate todo create for admin to add todo's to any user
def todo_admin_create(request):
    data = request.POST or None
    form = TodoAdminForm(data)
    if form.is_valid():
        todo = form.save()
        messages.success(request, "'{}' has been added for '{}'".
                        format(todo.description, todo.user))
        return redirect('todo_list')
    return render(request, "timepiece/todo/todo-create.html", {'form': form})

def todo_admin_edit(request, todo_id):
    todo = get_object_or_404(ToDo, id=todo_id)
    if request.method == "POST": 
        form = TodoLAdminForm(request.POST, instance=todo)
        if form.is_valid():
            form.save()
            return redirect('todo_list')
    else:
        form = TodoAdminForm(instance=todo)
    return render(request, "timepiece/todo/todo-edit.html", {'form': form})

#admin can see todo list for all users
class TodoAdminListView(ListView):
    queryset = ToDo.objects.filter(completed=False)
    template_name = "timepiece/todo/todo-list.html"

#admin can see completed todo's for all users
class TodoCompletedListView(ListView):
    queryset = ToDo.objects.filter(completed=True)
    template_name = "timepiece/todo/todo-complete-all.html"

