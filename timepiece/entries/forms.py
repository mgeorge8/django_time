import datetime
from dateutil.relativedelta import relativedelta

from django import forms
from django.db.models import Q

from timepiece import utils
from timepiece.manager.models import Project, ProjectRelationship
from timepiece.entries.models import Entry, ProjectHours, ToDo
from timepiece.forms import (
    INPUT_FORMATS, TimepieceSplitDateTimeField, TimepieceDateInput)


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(
        label='Notes for the active entry', widget=forms.Textarea(attrs={'rows':5, 'cols':90, 'maxlength': '50'}),
        required=False)
    start_time = TimepieceSplitDateTimeField(required=False)

    class Meta:
        model = Entry
        exclude = []
        fields = ('active_comment', 'project',
                  'start_time', 'activities')


    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.active = kwargs.pop('active', None)

        initial = kwargs.get('initial', {})
##        default_loc = utils.get_setting('TIMEPIECE_DEFAULT_LOCATION_SLUG')
##        if default_loc:
##            try:
##                loc = Location.objects.get(slug=default_loc)
##            except Location.DoesNotExist:
##                loc = None
##            if loc:
##                initial['location'] = loc.pk
        project = initial.get('project', None)
        try:
            last_project_entry = Entry.objects.filter(
                user=self.user, project=project).order_by('-end_time')[0]
        except IndexError:
            initial['project'] = None

        super(ClockInForm, self).__init__(*args, **kwargs)

        self.fields['start_time'].initial = datetime.datetime.now()
        self.fields['project'].queryset = Project.trackable.filter(
            users=self.user)
        if not self.active:
            self.fields.pop('active_comment')
        else:
            self.fields['active_comment'].initial = self.active.activities
        self.instance.user = self.user

    def clean_start_time(self):
        """
        Make sure that the start time doesn't come before the active entry
        """
        start = self.cleaned_data.get('start_time')
        if not start:
            return start
        active_entries = self.user.timepiece_entries.filter(
            start_time__gte=start, end_time__isnull=True)
        for entry in active_entries:
            output = ('The start time is on or before the current entry: '
                      '%s starting at %s' % (entry.project,
                                                  entry.start_time.strftime('%H:%M:%S')))
            raise forms.ValidationError(output)
        return start

    def clean(self):
        start_time = self.clean_start_time()
        data = self.cleaned_data
        if not start_time:
            return data
        if self.active:
            self.active.activities = data['active_comment']
            self.active.end_time = start_time - relativedelta(seconds=1)
            if not self.active.clean():
                raise forms.ValidationError(data)
        return data

    def save(self, commit=True):
        self.instance.hours = 0
        entry = super(ClockInForm, self).save(commit=commit)
        if self.active and commit:
            self.active.save()
        return entry


class ClockOutForm(forms.ModelForm):
    start_time = TimepieceSplitDateTimeField()
    end_time = TimepieceSplitDateTimeField()

    class Meta:
        model = Entry
        exclude = []
        fields = ('start_time', 'end_time')

    def __init__(self, *args, **kwargs):
        kwargs['initial'] = kwargs.get('initial', None) or {}
        kwargs['initial']['end_time'] = datetime.datetime.now()
        super(ClockOutForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        entry = super(ClockOutForm, self).save(commit=False)
        #entry.unpause(entry.end_time)
        if commit:
            entry.save()
        return entry


class AddUpdateEntryForm(forms.ModelForm):
    start_time = TimepieceSplitDateTimeField(initial=datetime.datetime.now())
    end_time = TimepieceSplitDateTimeField()

    class Meta:
        model = Entry
        exclude = ('user', 'site', 'hours', 'end')
        

    def __init__(self, *args, **kwargs):
        #kwargs['initial'] = kwargs.get('initial', None) or {}
        #kwargs['initial']['start_time'] = datetime.datetime.now()
        #kwargs['initial']['end_time'] = datetime.datetime.now()
        #initial = kwargs.get('initial', {})
        #self.fields['start_time'].initial = datetime.datetime.now()
        self.user = kwargs.pop('user')
        self.acting_user = kwargs.pop('acting_user')
        super(AddUpdateEntryForm, self).__init__(*args, **kwargs)
        self.instance.user = self.user
        self.fields['project'].queryset = Project.trackable.filter(
            users=self.user)
        # If editing the active entry, remove the end_time field.
        if self.instance.start_time and not self.instance.end_time:
            self.fields.pop('end_time')

    def clean(self):
        """
        If we're not editing the active entry, ensure that this entry doesn't
        conflict with or come after the active entry.
        """
        active = utils.get_active_entry(self.user)
        start_time = self.cleaned_data.get('start_time', None)
        end_time = self.cleaned_data.get('end_time', None)

        if active and active.pk != self.instance.pk:
            if (start_time and start_time > active.start_time) or \
                    (end_time and end_time > active.start_time):
                raise forms.ValidationError(
                    'The start time or end time conflict with the active '
                    'entry: {project} starting at '
                    '{start_time}.'.format(
                        project=active.project,
                        start_time=active.start_time.strftime('%H:%M:%S'),
                    ))

        month_start = utils.get_month_start(start_time)
        next_month = month_start + relativedelta(months=1)
        entries = self.instance.user.timepiece_entries.filter(
           # Q(status=Entry.APPROVED) | Q(status=Entry.INVOICED),
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        entry = self.instance

##        if not self.acting_user.is_superuser:
##            if (entries.exists() and not entry.id or entry.id and entry.status == Entry.INVOICED):
##                message = 'You cannot add/edit entries after a timesheet has been ' \
##                    'approved or invoiced. Please correct the start and end times.'
##                raise forms.ValidationError(message)

        return self.cleaned_data

class EntryDashboardForm(forms.ModelForm):
    start_time = TimepieceSplitDateTimeField()
    #end_time = TimepieceSplitDateTimeField(required=False)
    #end = forms.TimeField(required=False)
    end_date = forms.DateField(required=False, label="End time:")
    time_end = forms.TimeField(required=False, label="")

    class Meta:
        model = Entry
        exclude = ('user', 'site', 'hours', 'end', 'end_time')
        
        

    def __init__(self, *args, **kwargs):
        #kwargs['initial'] = kwargs.get('initial', None) or {}
        #kwargs['initial']['start_time'] = datetime.datetime.now()
        #kwargs['initial']['end_time'] = datetime.datetime.now()
        
        self.user = kwargs.pop('user')
        self.acting_user = kwargs.pop('acting_user')
        super(EntryDashboardForm, self).__init__(*args, **kwargs)
        self.instance.user = self.user
        self.fields['project'].queryset = Project.trackable.filter(
            users=self.user)
        #self.fields['end_time'].
        initial = kwargs.get('initial', {})
        #self.fields['start_time'].initial = datetime.datetime.now()
        # If editing the active entry, remove the end_time field.
        if self.instance.start_time and not self.instance.end_time:
            #self.fields['end_time'].initial = datetime.datetime.now()
            self.fields.pop('start_time')

##    def clean_end_time(self):
##        data = self.cleaned_data.get('end_time', None)
##        if data:
##            data = None
##        return data

    def clean(self):
        """
        If we're not editing the active entry, ensure that this entry doesn't
        conflict with or come after the active entry.
        """
        active = utils.get_active_entry(self.user)
        start_time = self.cleaned_data.get('start_time', None)
        time_end = self.cleaned_data.get('time_end', None)
        end_date = self.cleaned_data.get('end_date', None)
        if end_date and (time_end is None):
            raise forms.ValidationError("Must enter an end time.")
        if time_end and (end_date is None):
            raise forms.ValidationError("Must enter an end date.")
        if end_date and time_end:
            self.instance.end_time = datetime.datetime.combine(end_date, time_end)
        else:
            self.instance.end_time = None
        end_time = self.cleaned_data.get('end_time')
        #hours = end_time - start_time.time
##        if(end != None and active != None):
##            end_time = datetime.datetime.combine(active.start_time.date(), end)
##        elif (end != None and active == None):
##            end_time = datetime.datetime.combine(start_time.date(), end)
##        else:
##            end_time = None
        if active and active.pk != self.instance.pk:
            if (start_time and start_time > active.start_time) or \
                    (end_time and end_time > active.start_time):
                raise forms.ValidationError(
                    'The start time or end time conflict with the active '
                    'entry: {project} starting at '
                    '{start_time}.'.format(
                        project=active.project,
                        start_time=active.start_time.strftime('%H:%M:%S'),
                    ))

        month_start = utils.get_month_start(start_time)
        next_month = month_start + relativedelta(months=1)
        entries = self.instance.user.timepiece_entries.filter(
            #Q(status=Entry.APPROVED) | Q(status=Entry.INVOICED),
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        entry = self.instance

        return self.cleaned_data

    def save(self, commit=True):
        entry = super(EntryDashboardForm, self).save(commit=False)
##        if(entry.end != None):
##            entry.end_time = datetime.datetime.combine(entry.start_time.date(), entry.end)
        if commit:
            entry.save()
        return entry
    

class TodoListForm(forms.ModelForm):
    class Meta:
        model = ToDo
        fields = '__all__'

class TodoForm(forms.ModelForm):
    class Meta:
        model = ToDo
        fields = ['priority', 'description']
        exclude = ['user']

class ProjectHoursForm(forms.ModelForm):

    class Meta:
        model = ProjectHours
        fields = ['week_start', 'project', 'user', 'hours', 'published']

    def save(self, commit=True):
        ph = super(ProjectHoursForm, self).save()
        # since hours are being assigned to a user, add the user
        # to the project if they are not already in it so they can track time
        ProjectRelationship.objects.get_or_create(user=self.cleaned_data['user'],
                                                  project=self.cleaned_data['project'])
        return ph


class ProjectHoursSearchForm(forms.Form):
    week_start = forms.DateField(
        label='Week of', required=False,
        input_formats=INPUT_FORMATS, widget=TimepieceDateInput())

    def clean_week_start(self):
        week_start = self.cleaned_data.get('week_start', None)
        return utils.get_week_start(week_start, False) if week_start else None
