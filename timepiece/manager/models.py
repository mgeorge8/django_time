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
    ssn = models.CharField(max_length=4, blank=True, default = ' ')
    title = models.CharField(max_length=20, blank=True, default = ' ')
    payroll = models.BooleanField(default=True, blank=False)

    class Meta:
        db_table = 'manager_profile'  # Using legacy table name.
    
#used to get active projects
class TrackableProjectManager(models.Manager):

    def get_queryset(self):
        return super(TrackableProjectManager, self).get_queryset().filter(
            inactive=False,
        )


@python_2_unicode_compatible
class Project(models.Model):
    name = models.CharField(max_length=255)
    users = models.ManyToManyField(User, related_name='user_projects', through='ProjectRelationship')
    inactive = models.BooleanField(blank=False, default=False)
    objects = models.Manager()
    trackable = TrackableProjectManager()

    class Meta:
        db_table = 'timepiece_project'  # Using legacy table name.
        ordering = ('name',) 

    def __str__(self):
        return '{0}'.format(self.name)

    def get_absolute_url(self):
        return reverse('view_project', args=(self.pk,))

    def get_display_name(self):
        return self.name

#through model was used to track other fields that we got rid of
#kept through model for db compatibility
@python_2_unicode_compatible
class ProjectRelationship(models.Model):
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

##
