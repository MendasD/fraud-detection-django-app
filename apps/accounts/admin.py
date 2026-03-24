"""
apps/accounts/admin.py
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'email', 'get_full_name', 'role', 'is_active')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = UserAdmin.fieldsets + (
        ('Informations Fortal Bank', {
            'fields': ('role', 'department', 'phone', 'avatar', 'receive_alerts'),
        }),
    )
