from django.contrib import admin
from .models import Contact, SpamReport

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'owner', 'registered_user', 'created_at')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'phone_number', 'owner__phone_number', 'owner__name')
    raw_id_fields = ('owner', 'registered_user')

@admin.register(SpamReport)
class SpamReportAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'reported_by', 'reported_at')
    list_filter = ('reported_at',)
    search_fields = ('phone_number', 'reported_by__phone_number', 'reported_by__name')
    raw_id_fields = ('reported_by',)