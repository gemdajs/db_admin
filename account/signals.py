from django.db.models.signals import post_save
from django.dispatch import receiver

from account.models import DBSyncModelColumn


@receiver(post_save, sender=DBSyncModelColumn)
def update_admin_model(sender, instance, *args, **kwargs):
    is_created = kwargs['created']
    if not is_created:
        # this hack was meant to reload the registered models in django admin to pick the
        # configuration, but it's not working as expected atm
        from dbsync.admin import register_external_model
        register_external_model(refresh_mode=True)