import datetime, csv
from dateutil.relativedelta import relativedelta

from six.moves.urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    CreateView, DeleteView, DetailView, UpdateView, FormView, TemplateView, View)
from django.views.generic.list import ListView

from timepiece import utils
from timepiece.forms import YearMonthForm, UserYearMonthForm, UserForm
from django.forms.models import inlineformset_factory
from timepiece.templatetags.timepiece_tags import seconds_to_hours
#from timepiece.utils.csv import CSVViewMixin
#from timepiece.utils.search import SearchListView
from timepiece.utils.views import cbv_decorator, format_totals
from timepiece.entries.views import DashboardMixin, Dashboard

from timepiece.manager.forms import (
    CreateEditProjectForm, EditUserSettingsForm, EditUserForm,
    CreateUserForm, ProfileForm, EditProjectRelationshipForm,
    ProjectRelationshipFormSet, ProjectCreateForm, SelectMultipleUserForm)
from timepiece.manager.models import Project, ProjectRelationship, Profile
from timepiece.manager.utils import grouped_totals
from timepiece.entries.models import Entry


@login_required
def view_user_timesheet(request, user_id):
    # User can only view their own time sheet unless they have a permission.
    user = get_object_or_404(User, pk=user_id)
    has_perm = request.user.has_perm('entries.view_entry_summary')
    if not (has_perm or user.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')

    FormClass = UserYearMonthForm if has_perm else YearMonthForm
    form = FormClass(request.GET or None)
    if form.is_valid():
        if has_perm:
            from_date, to_date, form_user = form.save()
            if form_user and request.GET.get('yearmonth', None):
                # Redirect to form_user's time sheet.
                # Do not use request.GET in urlencode to prevent redirect
                # loop caused by yearmonth parameter.
                url = reverse('view_user_timesheet', args=(form_user.pk,))
                request_data = {
                    'month': from_date.month,
                    'year': from_date.year,
                    'user': form_user.pk,  # Keep so that user appears in form.
                }
                url += '?{0}'.format(urlencode(request_data))
                return HttpResponseRedirect(url)
        else:  # User must be viewing their own time sheet; no redirect needed.
            from_date, to_date = form.save()
        from_date = utils.add_timezone(from_date)
        to_date = utils.add_timezone(to_date)
    else:
        # Default to showing this month.
        from_date = utils.get_month_start()
        to_date = from_date + relativedelta(months=1)

    entries_qs = Entry.objects.filter(user=user)
    month_qs = entries_qs.timespan(from_date, span='month')
    extra_values = ('start_time', 'end_time',
                    'id', 'project__name')
    month_entries = month_qs.date_trunc('month', extra_values).order_by('start_time')
    # For grouped entries, back date up to the start of the week.
    first_week = utils.get_week_start(from_date)
    month_week = first_week + relativedelta(weeks=1)
    second_week = from_date + relativedelta(weeks=1)
    grouped_qs = entries_qs.timespan(first_week, to_date=to_date)
    intersection = grouped_qs.filter(
        start_time__lt=month_week, start_time__gte=from_date)
    week_qs = entries_qs.timespan(from_date, span='week')
    week2_qs = entries_qs.timespan(second_week, span='week')
    month2_projects = []
    for x in range(0,5):
        loop_date = first_week + relativedelta(weeks=x)
        weekq = entries_qs.timespan(loop_date, span='week')
        project2_entries = weekq.order_by().values('project__name').annotate(sum=Sum('hours')).order_by('-sum')
        project2_entries.week5 = loop_date.strftime('%b %e, %Y')
        month2_projects.append(project2_entries)
    
    totals = grouped_totals(grouped_qs) if month_entries else '' 
    project_entries = week_qs.order_by().values('project__name').annotate(sum=Sum('hours')).order_by('-sum')
    month_projects = week2_qs.order_by().values('project__name').annotate(sum=Sum('hours')).order_by('-sum')
    summary = Entry.summary(user, from_date, to_date)

    return render(request, 'timepiece/user/timesheet/view.html', {
        'year_month_form': form,
        'from_date': from_date,
        'to_date': to_date - relativedelta(days=1),
        'timesheet_user': user,
        'entries': month_entries,
        'grouped_totals': totals,
        'project_entries': project_entries,
        'month_projects': month_projects,
        'summary': summary,
        'month2_projects': month2_projects,
        'first_week': first_week,
        'month_week': month_week,
        'second_week': second_week,
        'week_qs': week_qs,
        
    })



# Project timesheets
class ProjectTimesheet(DetailView):
    template_name = 'timepiece/project/timesheet.html'
    model = Project
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'

    def get(self, *args, **kwargs):
        if 'csv' in self.request.GET:
            request_get = self.request.GET.copy()
            request_get.pop('csv')
            return_url = reverse('view_project_timesheet_csv',
                                 args=(self.get_object().pk,))
            return_url += '?%s' % urlencode(request_get)
            return redirect(return_url)
        return super(ProjectTimesheet, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProjectTimesheet, self).get_context_data(**kwargs)
        project = self.object
        year_month_form = YearMonthForm(self.request.GET or None)
        if self.request.GET and year_month_form.is_valid():
            from_date, to_date = year_month_form.save()
        else:
            date = utils.add_timezone(datetime.datetime.today())
            from_date = utils.get_month_start(date).date()
            to_date = from_date + relativedelta(months=1)
        entries_qs = Entry.objects
        entries_qs = entries_qs.timespan(from_date, span='month').filter(
            project=project
        )
        extra_values = ('start_time', 'end_time',
                        'id', 'project__name')

        month_entries = entries_qs.date_trunc('month', extra_values).order_by('start_time')
        if month_entries:
            format_totals(month_entries, "hours")

        total = entries_qs.aggregate(hours=Sum('hours'))['hours']
        if total:
            total = "{0:.2f}".format(total)
        user_entries = entries_qs.order_by().values('user__first_name', 'user__last_name')
        user_entries = user_entries.annotate(sum=Sum('hours')).order_by('-sum')
        if user_entries:
            format_totals(user_entries)
##        activity_entries = entries_qs.order_by().values('activity__name')
##        activity_entries = activity_entries.annotate(sum=Sum('hours')).order_by('-sum')
##        if activity_entries:
##            format_totals(activity_entries)

        context.update({
            'project': project,
            'year_month_form': year_month_form,
            'from_date': from_date,
            'to_date': to_date - relativedelta(days=1),
            'entries': month_entries,
            'total': total,
            'user_entries': user_entries,
            #'activity_entries': activity_entries,
        })
        return context

# Users


@cbv_decorator(login_required)
class EditSettings(UpdateView):
    form_class = EditUserSettingsForm
    template_name = 'timepiece/user/settings.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        messages.info(self.request, 'Your settings have been updated.')
        return self.request.GET.get('next', None) or reverse('dashboard')


class ListUsers(ListView):
    model = User
    redirect_if_one_result = True
    #search_fields = ['first_name__icontains', 'last_name__icontains',
     #                'email__icontains', 'username__icontains']
    template_name = 'timepiece/user/list.html'

    def get_context_data(self, **kwargs):
        context = super(ListUsers, self).get_context_data(**kwargs)
        return context

##    def get_queryset(self):
##        return super(ListUsers, self).get_queryset().select_related()

def week_timesheet(request, date):
    all_users = User.objects.filter(profile__payroll=True).select_related('profile')
    response = HttpResponse(content_type='text/csv')
    from_date = datetime.datetime.strptime(date, "%Y-%m-%d")
    date2 = utils.add_timezone(datetime.datetime.today()).date()
    
    response['Content-Disposition'] = 'attachment; filename="engimusing-llc-timesheet-%s.csv"' % date

    writer = csv.writer(response)
    writer.writerow(['last_name',
            'first_name',
            'ssn',
            'title',
            'regular_hours',
            'overtime_hours',
            'double_overtime_hours',
            'bonus',
            'commision',
            'paycheck_tips',
            'cash_tips',
            'correction_payment',
            'reimbursement',
            'personal_note',])
    for use1 in all_users:
        last_name = use1.last_name
        first_name = use1.first_name
        ssn = use1.profile.ssn
        title = use1.profile.title
        week_entries = Entry.objects.filter(user=use1).timespan(from_date, span='week')
        user_entries = week_entries.order_by().values('user__first_name', 'user__last_name')
        user_entries = user_entries.annotate(sum=Sum('hours')).order_by('-sum')
        hours = sum(entries['sum'] for entries in user_entries)
        hours = round(hours, 2)
        writer.writerow([last_name, first_name, ssn, title, hours])
       
            
        
    return response

class WeekTimesheetMixin(object):

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

        return super(WeekTimesheetMixin, self).dispatch(request, *args, **kwargs)

class WeekTimesheet(WeekTimesheetMixin, TemplateView):
    template_name = 'timepiece/user/weektimesheet.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if context['form'].is_valid():
            print ('yes done')
            entry = context['form'].save()
            
            url = reverse('week_timesheet', args=[entry.pk])
            #url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
            #return redirect('week_timesheet', user_id=entry.pk)
        return super(WeekTimesheet, self).render_to_response(context)
    
    def get_context_data(self, *args, **kwargs):
        context = super(WeekTimesheet, self).get_context_data(**kwargs)
        week_start = self.week_start
        week_end = week_start + relativedelta(days=7)

        form = UserForm(self.request.POST or None)
        
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        
        
        week_entry = Entry.objects.filter(user=user_id)
        week_entry = week_entry.timespan(week_start, span='week')
        week_entries = week_entry.select_related('project')
        user_entries = week_entry.order_by().values('user__first_name', 'user__last_name')
        user_entries = user_entries.annotate(sum=Sum('hours')).order_by('-sum')    
        if user_entries:
            hours = sum(entries['sum'] for entries in user_entries)
        else:
            hours = 0
        #weekq = Entry.timespan(loop_date, span='week')
        #project_entries = week_entry.order_by().values('project__name').annotate(sum=Sum('hours')).order_by('-sum')
        project_entries = week_entry.order_by().values('project__name').distinct()
        project_entries = project_entries.annotate(amount=Sum('amount')).order_by('-amount')
        for p in project_entries:
            p['activities'] = ",".join(week['activities'] for week in week_entry.filter(project__name=p['project__name']).order_by('activities').values('activities').distinct())

        context.update({
            'user': user,
            'hours': hours,
            'form': form,
            'project_entries': project_entries,
            'week_entries': week_entries,
            'week': self.week_start,
            'prev_week': self.week_start - relativedelta(days=7),
            'next_week': self.week_start + relativedelta(days=7),
            })
        return context                            

class ViewUser(DetailView):
    model = User
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/user/view.html'

    def get_context_data(self, **kwargs):
        #kwargs.update({'add_project_form': SelectProjectForm()})
        return super(ViewUser, self).get_context_data(**kwargs)


def CreateUser(request):
    if request.method == 'POST':
        user_form = CreateUserForm(request.POST, instance=request.user)
        profile = Profile.objects.create(user = request.user)
        profile_form = ProfileForm(request.POST, instance = request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile_form.save()
            messages.success(request, ('Your profile was successfully updated!'))
            return redirect(reverse('list_users'))
        else:
            messages.error(request, ('Please correct the error below.'))
    else:
        user_form = CreateUserForm(instance=request.user)
        profile = Profile.objects.create(user = request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    return render(request, 'timepiece/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })



@cbv_decorator(permission_required('auth.delete_user'))
class DeleteUser(DeleteView):
    model = User
    success_url = reverse_lazy('list_users')
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/delete_object.html'


@cbv_decorator(permission_required('auth.change_user'))
class EditUser(UpdateView):
    model = User
    form_class = EditUserForm
    template_name = 'timepiece/user/create_edit.html'
    pk_url_kwarg = 'user_id'


# Projects


class ListProjects(ListView):
    model = Project
    template_name = 'timepiece/project/list.html'
    queryset = Project.objects.filter(inactive=False)

    def get_context_data(self, **kwargs):
        context = super(ListProjects, self).get_context_data(**kwargs)
        return context


class ListInactiveProjects(ListView):
    model = Project
    template_name = 'timepiece/project/inactive_list.html'
    queryset = Project.objects.filter(inactive=True)

class ViewProject(DetailView):
    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/project/view.html'

    def get_context_data(self, **kwargs):
        kwargs.update({'add_user_form': SelectMultipleUserForm()})
        return super(ViewProject, self).get_context_data(**kwargs)

def ProjectCreate(request):
    users = User.objects.all()
    if request.method == "POST":
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            inactive = form.cleaned_data['inactive']
            users = form.cleaned_data['users']
            project = Project(name=name, inactive=inactive)
            project.save()
            project_id = get_object_or_404(Project, pk=project.id)
            for user in users:
                ProjectRelationship.objects.get_or_create(user=user, project=project_id)
            return redirect(reverse('list_projects'))
    else:
        form = ProjectCreateForm()
    return render(request, "timepiece/projectcreate.html", {"form": form, "users": users})

def ProjectEdit(request, project_id):
    project_instance = get_object_or_404(Project, pk=project_id)
    if request.method == "POST":
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            project_instance.name = form.cleaned_data['name']
            project_instance.inactive = form.cleaned_data['inactive']
            users = form.cleaned_data['users']
            #project = Project(name=name, inactive=inactive)
            project_instance.save()
            #project_id = get_object_or_404(Project, pk=project_insance.id)
            for user in project_instance.users.all():
                if user not in users:
                    rel = ProjectRelationship.objects.filter(user=user, project=project_instance)
                    try:
                        relation = rel.get()
                        relation.delete()
                    except:
                        raise ValidationError(_('Could not delete relationship'),)
            for user in users:
                ProjectRelationship.objects.update_or_create(user=user, project=project_instance)
            return redirect(reverse('list_projects'))
    else:
        form = ProjectCreateForm(initial={'name': project_instance.name,
                                          'inactive': project_instance.inactive,
                                          'users': project_instance.users.all()})
    return render(request, "timepiece/projectcreate.html", {"form": form})
    
##class CreateProject(CreateView):
##    form_class = CreateEditProjectForm
##    template_name = 'timepiece/project/createproject.html'
##    success_url = reverse_lazy('list_projects')
##
##    def get(self, request, *args, **kwargs):
##        self.object = None
##        form_class = self.get_form_class()
##        form = self.get_form(form_class)
##        project_formset = ProjectRelationshipFormSet()
##        return self.render_to_response(
##            self.get_context_data(form=form, project_formset=project_formset))
##
##    def post(self, request, *args, **kwargs):
##        self.object = None
##        form_class = self.get_form_class()
##        form = self.get_form(form_class)
##        project_formset = ProjectRelationshipFormSet(request.POST)
##        if (form.is_valid() and project_formset.is_valid()):
##            return self.form_valid(form, project_formset)
##        else:
##            return self.form_invalid(form, project_formset)
##
##    def form_valid(self, form, project_formset):
##        self.object = form.save()
##        project_formset.instance = self.object
##        project_formset.save()
##        return super(CreateProject, self).form_valid(form)
##
##    def form_invalid(self, form, project_formset):
##        return self.render_to_response(
##            self.get_context_data(form=form,project_formset=project_formset))

class EditProject(UpdateView):
    model = Project
    form_class = CreateEditProjectForm
    template_name = 'timepiece/project/editproject.html'
    pk_url_kwarg = 'project_id'

    success_url = reverse_lazy('list_projects')

    def get(self, request, *args, **kwargs):
        #self.object = None
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        project_formset = ProjectRelationshipFormSet(instance = self.object)
        return self.render_to_response(
            self.get_context_data(form=form, project_formset=project_formset))

    def post(self, request, *args, **kwargs):
        #self.object = None
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        project_formset = ProjectRelationshipFormSet(self.request.POST, instance=self.object)
        if (form.is_valid() and project_formset.is_valid()):
            return self.form_valid(form, project_formset)
        else:
            return self.form_invalid(form, project_formset)

    def form_valid(self, form, project_formset):
        self.object = form.save()
        project_formset.instance = self.object
        project_formset.save()
        return HttpResponseRedirect(self.get_success_url())
        #return super(CreateProject, self).form_valid(form)

    def form_invalid(self, form, project_formset):
        return self.render_to_response(
            self.get_context_data(form=form, project_formset=project_formset))



class DeleteProject(DeleteView):
    model = Project
    success_url = reverse_lazy('list_projects')
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/delete_object.html'


class CreateRelationship(View):

    def post(self, request, *args, **kwargs):
        users = self.get_user()
        project = self.get_project()
        for user in users:
            ProjectRelationship.objects.get_or_create(user=user, project=project)
        redirect_to = request.GET.get('next', None) or reverse('dashboard')
        return HttpResponseRedirect(redirect_to)

    def get_user(self):
        user_id = self.request.GET.get('user_id', None)
        if user_id:
            return get_object_or_404(User, pk=user_id)
        return SelectMultipleUserForm(self.request.POST).get_user()

    def get_project(self):
        project_id = self.request.GET.get('project_id', None)
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return SelectProjectForm(self.request.POST).get_project()


class RelationshipObjectMixin(object):
    """Handles retrieving and redirecting for ProjectRelationship objects."""

    def get_object(self, queryset=None):
        queryset = self.get_queryset() if queryset is None else queryset
        user_id = self.request.GET.get('user_id', None)
        project_id = self.request.GET.get('project_id', None)
        return get_object_or_404(self.model, user__id=user_id, project__id=project_id)

    def get_success_url(self):
        return self.request.GET.get('next', self.object.project.get_absolute_url())


class DeleteRelationship(RelationshipObjectMixin, DeleteView):
    model = ProjectRelationship
    template_name = 'timepiece/relationship/delete.html'
    
