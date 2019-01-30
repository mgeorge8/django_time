from redirect.models import Redirect
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

"""everytime a redirect is deleted/updated, cache deleted to ensure accuracy.
cache is set in middleware"""
@receiver(post_save, sender=Redirect)
@receiver(post_delete, sender=Redirect)
def reset_cache(sender, instance, **kwargs):
    path = instance.old_path
    cache.delete(path)
