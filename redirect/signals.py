from redirect.models import Redirect
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=Redirect)
@receiver(post_delete, sender=Redirect)
def reset_cache(sender, instance, **kwargs):
    path = instance.old_path
    cache.delete(path)
