import datetime
from dateutil.relativedelta import relativedelta

from django import forms
from django.db.models import Q

from timepiece import utils
from timepiece.manager.models import Project
from timepiece.entries.models import Entry, ToDo
from timepiece.forms import TimepieceSplitDateTimeField


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(
        label='Notes for the active entry', widget=forms.Textarea(attrs={'rows':5, 'cols':90, 'maxlength': '50'}),
        required=False)
    start_time = TimepieceSplitDateTimeField()

    class Meta:
        model = Entry
        exclude = []
        fields = ('active_comment', 'project',
                  'start_time', 'activities')


    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.active = kwargs.pop('active', None)

        initial = kwargs.get('initial', {})
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
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        entry = self.instance
        return self.cleaned_data

class EntryDashboardForm(forms.ModelForm):
    start_time = TimepieceSplitDateTimeField()
    #just time for end time, gets date from start time
    end = forms.TimeField(required=False)

    class Meta:
        model = Entry
        exclude = ('user', 'site', 'hours', 'end_time') 
        

    def __init__(self, *args, **kwargs):        
        self.user = kwargs.pop('user')
        self.acting_user = kwargs.pop('acting_user')
        super(EntryDashboardForm, self).__init__(*args, **kwargs)
        self.instance.user = self.user
        self.fields['project'].queryset = Project.trackable.filter(
            users=self.user)
        initial = kwargs.get('initial', {})
        # If editing the active entry, remove the end_time field.
        if self.instance.start_time and not self.instance.end_time:
            self.fields.pop('start_time')


    def clean(self):
        """
        If we're not editing the active entry, ensure that this entry doesn't
        conflict with or come after the active entry.
        """
        active = utils.get_active_entry(self.user)
        start_time = self.cleaned_data.get('start_time', None)
        end = self.cleaned_data.get('end', None)
        if(end != None and active != None):
            end_time = datetime.datetime.combine(active.start_time.date(), end)
        elif (end != None and active == None):
            end_time = datetime.datetime.combine(start_time.date(), end)
        else:
            end_time = None
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
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        entry = self.instance

        return self.cleaned_data

    def save(self, commit=True):
        entry = super(EntryDashboardForm, self).save(commit=False)
        if(entry.end != None):
            entry.end_time = datetime.datetime.combine(entry.start_time.date(), entry.end)
        if commit:
            entry.save()
        return entry
    

class TodoAdminForm(forms.ModelForm):
    class Meta:
        model = ToDo
        fields = '__all__'

#for signed in user, don't need to select user
class TodoForm(forms.ModelForm):
    class Meta:
        model = ToDo
        fields = ['priority', 'description']
        exclude = ['user']


