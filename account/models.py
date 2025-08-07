import re

from django.contrib.auth.models import AbstractUser
from django.db import models


class DBSyncUser(AbstractUser):
    USERNAME_FIELD = "username"

    def get_short_name(self):
        return self.get_full_name()

    def get_full_name(self):
        name = " ".join([self.first_name or "", self.last_name or ""])
        return re.sub(r"\s+", " ", name).strip()

    def has_module_perms(self, app_label):
        return self.is_superuser or "dbsync" == app_label

    def natural_key(self):
        return self.email

    def __str__(self):
        return self.get_full_name() + f" ({self.username})"


class DBSyncModelColumn(models.Model):
    model = models.CharField(max_length=500)
    name = models.CharField(max_length=500)
    in_searchable_list = models.BooleanField(default=False)
    in_list_filter_list = models.BooleanField(default=False)
    in_list_display_list = models.BooleanField(default=True)
    in_autocomplete_list = models.BooleanField(default=False)
    in_readonly_list = models.BooleanField(default=False)
    is_foreign_key = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    repr_order = models.PositiveIntegerField(null=True, blank=True, default=None, db_comment="This is the order which this should be in __str__")

    class Meta:
        unique_together = (("model", "name"), )
        ordering = ("model", "name",)

    def __str__(self):
        return "{} - {}".format(self.model, self.name)
