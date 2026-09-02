from django.contrib import admin

from .models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'organization')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'organization__name', 'email', 'phone')
