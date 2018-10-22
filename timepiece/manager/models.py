from collections import OrderedDict

from django.apps import apps
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.db.models.signals import post_save
from django.dispatch import receiver

from timepiece.utils import get_active_entry


# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
_clocked_in = lambda user: bool(get_active_entry(user))
User.add_to_class('clocked_in', property(_clocked_in))


# Utility method to get user's name, falling back to username.
_get_name_or_username = lambda user: user.get_full_name() or user.username
User.add_to_class('get_name_or_username', _get_name_or_username)


_get_absolute_url = lambda user: reverse('view_user', args=(user.pk,))
User.add_to_class('get_absolute_url', _get_absolute_url)


@python_2_unicode_compatible
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    #hours_per_week = models.DecimalField(
       # max_digits=8, decimal_places=2, default=40)
    ssn = models.CharField(max_length=4, blank=True, default = ' ')
    title = models.CharField(max_length=20, blank=True, default = ' ')

    class Meta:
        db_table = 'manager_profile'  # Using legacy table name.

    """def __unicode__(self):
        return self.user.username"""
    

##class TypeAttributeManager(models.Manager):
##    """Object manager for type attributes."""
##
##    def get_queryset(self):
##        qs = super(TypeAttributeManager, self).get_queryset()
##        return qs.filter(type=Attribute.PROJECT_TYPE)
##
##
##class StatusAttributeManager(models.Manager):
##    """Object manager for status attributes."""
##
##    def get_queryset(self):
##        qs = super(StatusAttributeManager, self).get_queryset()
##        return qs.filter(type=Attribute.PROJECT_STATUS)
##
##
##@python_2_unicode_compatible
##class Attribute(models.Model):
##    PROJECT_TYPE = 'project-type'
##    PROJECT_STATUS = 'project-status'
##    ATTRIBUTE_TYPES = OrderedDict((
##        (PROJECT_TYPE, 'Project Type'),
##        (PROJECT_STATUS, 'Project Status'),
##    ))
##    SORT_ORDER_CHOICES = [(x, x) for x in range(-20, 21)]
##
##    type = models.CharField(max_length=32, choices=ATTRIBUTE_TYPES.items())
##    label = models.CharField(max_length=255)
##    sort_order = models.SmallIntegerField(
##        null=True, blank=True, choices=SORT_ORDER_CHOICES)
##    enable_timetracking = models.BooleanField(
##        default=False,
##        help_text=('Enable time tracking functionality for projects '
##                   'with this type or status.'))
##    billable = models.BooleanField(default=False)
##
##    objects = models.Manager()
##    types = TypeAttributeManager()
##    statuses = StatusAttributeManager()
##
##    class Meta:
##        db_table = 'timepiece_attribute'  # Using legacy table name.
##        unique_together = ('type', 'label')
##        ordering = ('sort_order',)
##
##    def __str__(self):
##        return self.label
##
##
##@python_2_unicode_compatible
##class Business(models.Model):
##    name = models.CharField(max_length=255)
##    short_name = models.CharField(max_length=255, blank=True)
##    email = models.EmailField(blank=True)
##    description = models.TextField(blank=True)
##    notes = models.TextField(blank=True)
##    external_id = models.CharField(max_length=32, blank=True)
##
##    class Meta:
##        db_table = 'timepiece_business'  # Using legacy table name.
##        ordering = ('name',)
##        verbose_name_plural = 'Businesses'
##        permissions = (
##            ('view_business', 'Can view businesses'),
##        )
##
##    def __str__(self):
##        return self.get_display_name()
##
##    def get_absolute_url(self):
##        return reverse('view_business', args=(self.pk,))
##
##    def get_display_name(self):
##        return self.short_name or self.name
##
##
class TrackableProjectManager(models.Manager):

    def get_queryset(self):
        return super(TrackableProjectManager, self).get_queryset().filter(
            inactive=False,
            #status__enable_timetracking=True,
            #type__enable_timetracking=True,
        )


@python_2_unicode_compatible
class Project(models.Model):
    name = models.CharField(max_length=255)
    users = models.ManyToManyField(User, related_name='user_projects', through='ProjectRelationship')
    inactive = models.BooleanField(blank=False, default=False)
    #activity_group = models.ForeignKey(
     #   'entries.ActivityGroup', related_name='activity_group', null=True,
      #  blank=True, verbose_name='restrict activities to')
##    type = models.ForeignKey(
##        Attribute, limit_choices_to={'type': 'project-type'},
##        related_name='projects_with_type', null=True, blank=True, on_delete=models.CASCADE,)
##    status = models.ForeignKey(
##        Attribute, limit_choices_to={'type': 'project-status'},
##        related_name='projects_with_status', null=True, blank=True, on_delete=models.CASCADE,)
##    description = models.TextField(blank=True, null=True)

    objects = models.Manager()
    trackable = TrackableProjectManager()

    class Meta:
        db_table = 'timepiece_project'  # Using legacy table name.
        ordering = ('name',) #'status', 'type',)
        #permissions = ( )

    def __str__(self):
        return '{0}'.format(self.name)

##    @property
##    def billable(self):
##        return self.type.billable

    def get_absolute_url(self):
        return reverse('view_project', args=(self.pk,))

##    def get_active_contracts(self):
##        Returns all associated contracts which are not marked complete.
##        ProjectContract = apps.get_model('contracts', 'ProjectContract')
##        return self.contracts.exclude(status=ProjectContract.STATUS_COMPLETE)

    def get_display_name(self):
        return self.name

##@python_2_unicode_compatible
##class RelationshipType(models.Model):
##    name = models.CharField(max_length=255, unique=True)
##    slug = models.SlugField(max_length=255)
##
##    class Meta:
##        db_table = 'timepiece_relationshiptype'  # Using legacy table name.
##
##    def __str__(self):
##        return self.name


@python_2_unicode_compatible
class ProjectRelationship(models.Model):
    #types = models.ManyToManyField(
       # RelationshipType, blank=True, related_name='project_relationships')
    user = models.ForeignKey(User, related_name='project_relationships', on_delete=models.CASCADE,)
    project = models.ForeignKey(Project, related_name='project_relationships', on_delete=models.CASCADE,)

    class Meta:
        db_table = 'timepiece_projectrelationship'  # Using legacy table name.
        unique_together = ('user', 'project')

    def __str__(self):
        return "{project}'s relationship to {user}".format(
            project=self.project.name,
            user=self.user.get_name_or_username(),
        )

        
##@python_2_unicode_compatible
##class Item_Type(models.Model):
##    name = models.CharField(max_length=255)
##    tracker_url = models.CharField(
##        max_length=255, blank=True, null=False, default="")
##    description = models.TextField( blank=True )
##
##    count = models.PositiveIntegerField(
##        default=0)
##        
##    class Meta:
##        db_table = 'timepiece_item_type'  # Using legacy table name.
##        ordering = ('name', 'count',)
##        permissions = (
##            ('view_inventory', 'Can view item type'),
##        )
##
##    def __str__(self):
##        return '{0}'.format(self.name)
##        
##    def get_display_name(self):
##        return self.name
##        
##    def get_absolute_url(self):
##        return reverse('view_item_type', args=(self.pk,))
##
