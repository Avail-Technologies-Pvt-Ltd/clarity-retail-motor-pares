from django.contrib import admin

from .models import Printer


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "display_name",
        "server_ip",
        "server_port",
        "enabled",
        "is_default",
    )

    list_filter = (
        "enabled",
        "is_default",
    )

    search_fields = (
        "name",
        "display_name",
        "server_ip",
    )