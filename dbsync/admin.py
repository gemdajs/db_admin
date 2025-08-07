import json
from typing import Any
import sys

from django.contrib import admin

from account.models import DBSyncModelColumn
from utils.dbsync_util import app_models
from utils.log_util import AppLogger


def make_display_hook(field_name):
    def _display(self, obj):
        try:
            if not hasattr(obj, field_name):
                return None

            val = getattr(obj, field_name, None)

            if val is None:
                return None

            if isinstance(val, (dict, list)):
                return json.dumps(val, indent=2)

            return str(val)
        except Exception:
            return None

    _display.short_description = field_name.replace('_', ' ').title()
    _display.admin_order_field = field_name
    return _display


def register_external_model(refresh_mode=False):
    class CustomAdmin(admin.ModelAdmin):

        list_display = []

        autocomplete_fields = []
        search_fields = []

    models, foreign_fields, _, model_fields, *_ = app_models
    for name, model_cls in models.items():
        try:
            autocomplete_fields = []
            display_fields = []
            search_fields = []
            filter_fields = []

            for model_field in DBSyncModelColumn.objects.filter(model=name).order_by("order"):
                field = model_field.name
                if model_field.is_foreign_key:
                    d_field = field[:-3] if field.endswith("_id") else field
                else:
                    d_field = field

                if model_field.in_list_display_list:
                    method_name = f"d_{d_field}"
                    display_method = make_display_hook(field)

                    setattr(CustomAdmin, method_name, display_method)
                    display_fields.append(method_name)

                if model_field.in_autocomplete_list and model_field.is_foreign_key:
                    autocomplete_fields.append(d_field)

                if model_field.in_searchable_list:
                    search_fields.append(field)

                if model_field.in_list_filter_list:
                    filter_fields.append(field)

            admin_cls: Any = type(
                f"{model_cls.__name__}Admin", (CustomAdmin,),
                {
                    "autocomplete_fields": autocomplete_fields,
                    "search_fields": search_fields,
                    "list_display": display_fields,
                    "list_filter": filter_fields
                }
            )
            if refresh_mode:
                try:
                    # todo: this does not seem to be working as intended, we hooked on post_save for
                    admin.site.unregister(model_cls)
                except Exception as e:
                    AppLogger.report(e)

            admin.site.register(model_cls, admin_cls)
        except Exception as e:
            AppLogger.report(e)


def is_runserver_or_wsgi():
    return 'runserver' in sys.argv or 'gunicorn' in sys.argv

if is_runserver_or_wsgi():
    register_external_model()
