from django.contrib import admin

from account.models import DBSyncUser, DBSyncModelColumn


@admin.register(DBSyncUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "first_name", "last_name", "email", "is_active"]

    autocomplete_fields = []
    search_fields = ["username", "first_name", "last_name", "email"]


@admin.register(DBSyncModelColumn)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "model", "name", "description", "in_list_display_list", "in_list_filter_list", "in_searchable_list", "in_autocomplete_list"]

    autocomplete_fields = []
    list_filter = ["model"]
    search_fields = ["name"]
    readonly_fields = ["is_foreign_key"]
