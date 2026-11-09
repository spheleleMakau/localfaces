from django.contrib import admin

from .models import TrainingOrder


@admin.register(TrainingOrder)
class TrainingOrderAdmin(admin.ModelAdmin):
    list_display = ("token", "first_name", "last_name", "email", "total", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("token", "first_name", "last_name", "email", "payfast_payment_id")
    readonly_fields = ("token", "first_name", "last_name", "email", "items", "total", "status", "payfast_payment_id", "created_at")

    def has_add_permission(self, request):
        return False
