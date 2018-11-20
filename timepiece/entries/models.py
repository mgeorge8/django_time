from collections import OrderedDict
from decimal import Decimal
import datetime

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q, Sum, Max, Min
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from timepiece import utils
from timepiece.manager.models import Project


class EntryQuerySet(models.query.QuerySet):
    """QuerySet extension to provide filtering by billable status"""

    def date_trunc(self, key='month', extra_values=None):
        select = {
            "day": {"date": """DATE_TRUNC('day', end_time)"""},
            "week": {"date": """DATE_TRUNC('week', end_time)"""},
            "month": {"date": """DATE_TRUNC('month', end_time)"""},
            "year": {"date": """DATE_TRUNC('year', end_time)"""},
        }
        basic_values = (
            'user', 'date', 'user__first_name', 'user__last_name')
        
        extra_values = extra_values or ()
        qs = self.extra(select=select[key])
        qs = qs.values(*basic_values + extra_values)
        qs = qs.annotate(hours=Sum('hours')).order_by(
            'user__last_name',
            'user__first_name',
            'user__pk',
            'date')
        return qs

    def timespan(self, from_date, to_date=None, span=None, current=False):
        """
        Takes a beginning date a filters entries. An optional to_date can be
        specified, or a span, which is one of ('month', 'week', 'day').
        N.B. - If given a to_date, it does not include that date, only before.
        """
        if span and not to_date:
            diff = None
            if span == 'month':
                diff = relativedelta(months=1)
            elif span == 'week':
                diff = relativedelta(days=7)
            elif span == 'day':
                diff = relativedelta(days=1)
            if diff is not None:
                to_date = from_date + diff
        datesQ = Q(end_time__gte=from_date)
        datesQ &= Q(end_time__lt=to_date) if to_date else Q()
        datesQ |= Q(end_time__isnull=True) if current else Q()
        return self.filter(datesQ)


class EntryManager(models.Manager):

    def get_queryset(self):
        qs = EntryQuerySet(self.model)
        #qs = qs.select_related('project__name')

        # ensure our select_related are added.  Without this line later calls
        # to select_related will void ours (not sure why - probably a bug
        # in Django)
        # in other words: do not remove!
        str(qs.query)
        return qs

    def date_trunc(self, key='month', extra_values=()):
        return self.get_queryset().date_trunc(key, extra_values)

    def timespan(self, from_date, to_date=None, span='month'):
        return self.get_queryset().timespan(from_date, to_date, span)


class ToDo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,)
    priority = models.IntegerField()
    description = models.CharField(max_length=50, blank=False)
    completed = models.BooleanField(blank=False, default=False)

    class Meta:
        ordering = ["user", "priority"]

    def __str__(self):
        return self.description

@python_2_unicode_compatible
class Entry(models.Model):
    """
    This class is where all of the time logs are taken care of
    """
    user = models.ForeignKey(User, related_name='timepiece_entries', on_delete=models.CASCADE,)
   # project = models.CharField(max_length=50, blank=False)
    project = models.ForeignKey('manager.Project', related_name='entries', on_delete=models.CASCADE,)    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True, db_index=True)
    end = models.TimeField(blank=True, null=True)
    activities = models.CharField(max_length=50, blank=False)
    date_updated = models.DateTimeField(auto_now=True)
    hours = models.DecimalField(max_digits=11, decimal_places=5, default=0)

    objects = EntryManager()
    #worked = EntryWorkedManager()
    no_join = models.Manager()

    class Meta:
        db_table = 'timepiece_entry'  # Using legacy table name
        ordering = ('-start_time',)
        verbose_name_plural = 'entries'
        permissions = (
            ('can_clock_in', 'Can use Pendulum to clock in'),
            ('can_clock_out', 'Can use Pendulum to clock out'),
        )

    def __str__(self):
        return '%s on %s' % (self.user, self.project)

    def check_overlap(self, entry_b, **kwargs):
        """Return True if the two entries overlap."""
        consider_pause = False #kwargs.get('pause', True)
        entry_a = self
        # if entries are open, consider them to be closed right now
        if not entry_a.end_time or not entry_b.end_time:
            return False
        # Check the two entries against each other
        start_inside = entry_a.start_time > entry_b.start_time \
            and entry_a.start_time < entry_b.end_time
        """end_inside = entry_a.end_time > entry_b.start_time \
            and entry_a.end_time < entry_b.end_time"""
        a_is_inside = entry_a.start_time > entry_b.start_time \
            and entry_a.end_time < entry_b.end_time
        b_is_inside = entry_a.start_time < entry_b.start_time \
            and entry_a.end_time > entry_b.end_time
        overlap = start_inside or """end_inside""" or a_is_inside or b_is_inside
        if not consider_pause:
            return overlap
        else:
            if overlap:
                max_end = max(entry_a.end_time, entry_b.end_time)
                min_start = min(entry_a.start_time, entry_b.start_time)
                diff = max_end - min_start
                diff = diff.seconds + diff.days * 86400
                total = entry_a.get_total_seconds() + entry_b.get_total_seconds() - 1
                if total >= diff:
                    return True
            return False

    def is_overlapping(self):
        if self.start_time and self.end_time:
            entries = self.user.timepiece_entries.filter(
                Q(end_time__range=(self.start_time, self.end_time)) |
                Q(start_time__range=(self.start_time, self.end_time)) |
                Q(start_time__lte=self.start_time, end_time__gte=self.end_time)
            )

            totals = entries.aggregate(max=Max('end_time'), min=Min('start_time'))

            totals['total'] = 0
            for entry in entries:
                totals['total'] = totals['total'] + entry.get_total_seconds()

            totals['diff'] = totals['max'] - totals['min']
            totals['diff'] = totals['diff'].seconds + \
                totals['diff'].days * 86400

            if totals['total'] > totals['diff']:
                return False
            else:
                return False
        else:
            return None

    def clean(self):
        if not self.user_id:
            raise ValidationError('An unexpected error has occured')
        if not self.start_time:
            raise ValidationError('Please enter a valid start time')
        start = self.start_time

        if self.end_time:
            end = self.end_time - relativedelta(seconds=1)
        # Current entries have no end_time
        elif self.end:
            end = datetime.datetime.combine(self.start_time.date(), self.end)
        else:
            end = start + relativedelta(seconds=1)

##        if self.end:
##            end2 = self.end
##        else:
##            end2 = start.time()

        entries = self.user.timepiece_entries.filter(
            end_time__gt=start, start_time__lte=end)

        # An entry can not conflict with itself so remove it from the list
        if self.id:
            entries = entries.exclude(pk=self.id)
        for entry in entries:
            entry_data = {
                'project': entry.project,
                'start_time': entry.start_time,
                'end_time': entry.end_time, #- relativedelta(seconds=1)
                'endTime': entry.end,
            }
            # Conflicting saved entries
            if entry.end_time:
                if entry.start_time.date() == start.date() and entry.end_time.date() == end.date():
                    entry_data['start_time'] = entry.start_time.strftime(
                        '%H:%M:%S')
                    entry_data['end_time'] = entry.end_time.strftime(
                        '%H:%M:%S')
                    raise ValidationError('Start time overlaps with '
                                          '{project} from {start_time} to '
                                          '{end_time}.'.format(**entry_data))
                else:
                    entry_data['start_time'] = entry.start_time.strftime(
                        '%H:%M:%S on %m\%d\%Y')
                    entry_data['end_time'] = entry.end_time.strftime(
                        '%H:%M:%S on %m\%d\%Y')
                    raise ValidationError(
                        'Start time overlaps with {project} '
                        'from {start_time} to {end_time}.'.format(**entry_data))
##            elif entry.end:
##                entry_data['start_time'] = entry.start_time.strftime(
##                    '%H:%M:%S')
##                entry_data['endTime'] = entry.end.strftime(
##                    '%H:%M:%S')
##                raise ValidationError('Start time overlaps with '
##                                      '{project} from {start_time} to '
##                                      '{endTime}.'.format(**entry_data))
                
                
        
        if end <= start:
            raise ValidationError('Ending time must exceed the starting time')
##        if end2 < start.time():
##            raise ValidationError('Ending time must exceed the starting time')
            
        delta = (end - start)
        delta_secs = (delta.seconds + delta.days * 24 * 60 * 60)
        limit_secs = 60 * 60 * 12
        if delta_secs > limit_secs: 
            err_msg = 'Ending time exceeds starting time by 12 hours or more '\
                'for {0} on {1} at {2} to {3} at {4}.'.format(
                    self.project,
                    start.strftime('%m/%d/%Y'),
                    start.strftime('%H:%M:%S'),
                    end.strftime('%m/%d/%Y'),
                    end.strftime('%H:%M:%S')
                )
            raise ValidationError(err_msg)
        return True

    def save(self, *args, **kwargs):
        self.hours = Decimal('%.5f' % round(self.total_hours, 5))
        super(Entry, self).save(*args, **kwargs)

    def get_total_seconds(self):
        """
        Determines the total number of seconds between the starting and
        ending times of this entry. If the entry is paused, the end_time is
        assumed to be the pause time. If the entry is active but not paused,
        the end_time is assumed to be now.
        """
        start = self.start_time
        end = self.end_time
        if not end:
            end = timezone.now()
        delta = end - start
        seconds = delta.seconds
        return seconds + (delta.days * 86400)


    @property
    def total_hours(self):
        """
        Determined the total number of hours worked in this entry
        """
        total = self.get_total_seconds() / 3600.0
        # in case seconds paused are greater than the elapsed time
        if total < 0:
            total = 0
        return total

    @property
    def is_paused(self):
        """
        Determine whether or not this entry is paused
        """
        return False

    @property
    def is_closed(self):
        """
        Determine whether this entry has been closed or not
        """
        return bool(self.end_time)

    @property
    def is_editable(self):
        return True

    @property
    def delete_key(self):
        """
        Make it a little more interesting for deleting logs
        """
        salt = '%i-%i-apple-%s-sauce' \
            % (self.id, self.is_paused, self.is_closed)
        try:
            import hashlib
        except ImportError:
            import sha
            key = sha.new(salt.encode('utf-8')).hexdigest()
        else:
            key = hashlib.sha1(salt.encode('utf-8')).hexdigest()
        return key

    @staticmethod
    def summary(user, date, end_date):
        """
        Returns a summary of hours worked in the given time frame, for this
        user.  The setting TIMEPIECE_PAID_LEAVE_PROJECTS can be used to
        separate out hours for paid leave that should not be included in the
        total worked (e.g., sick time, vacation time, etc.).  Those hours will
        be added to the summary separately using the dictionary key set in
        TIMEPIECE_PAID_LEAVE_PROJECTS.
        """
        entries = user.timepiece_entries.filter(
            end_time__gt=date, end_time__lt=end_date)
        data = {
           'total': Decimal('0'),
           }
        total = entries.aggregate(s=Sum('hours'))['s']
        if total:
            data['total'] = total
        return data


@python_2_unicode_compatible
class ProjectHours(models.Model):
    week_start = models.DateField(verbose_name='start of week')
    project = models.ForeignKey('manager.Project', on_delete=models.CASCADE,)
    user = models.ForeignKey(User, on_delete=models.CASCADE,)
    hours = models.DecimalField(
        max_digits=11, decimal_places=5, default=0,
        validators=[validators.MinValueValidator(Decimal("0.00001"))])
    published = models.BooleanField(default=False)

    def __str__(self):
        return "{0} on {1} for Week of {2}".format(
            self.user.get_name_or_username(),
            self.project, self.week_start.strftime('%B %d, %Y'))

    def save(self, *args, **kwargs):
        # Ensure that week_start is the Monday of a given week.
        self.week_start = utils.get_week_start(self.week_start)
        return super(ProjectHours, self).save(*args, **kwargs)

    class Meta:
        db_table = 'timepiece_projecthours'  # Using legacy table name
        verbose_name = 'project hours entry'
        verbose_name_plural = 'project hours entries'
        unique_together = ('week_start', 'project', 'user')
