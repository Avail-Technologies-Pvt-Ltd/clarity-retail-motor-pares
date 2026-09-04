from django.urls import path

from . import views


app_name = "print_out"


urlpatterns = [
    path("api/", views.printer_list, name="printer_list"),
    path("api/add/", views.printer_add, name="printer_add"),
    path("api/<int:printer_id>/update/", views.printer_update, name="printer_update"),
    path("api/<int:printer_id>/delete/", views.printer_delete, name="printer_delete"),
    path("api/<int:printer_id>/test/", views.printer_test, name="printer_test"),
    path("api/<int:printer_id>/print/", views.printer_print_text, name="printer_print_text"),
    path("api/<int:printer_id>/default/", views.printer_set_default, name="printer_set_default"),
    path("api/<int:printer_id>/health/", views.printer_health, name="printer_health"),
    path("printers/<int:printer_id>/print/", views.printer_print_document, name="printer_print_document"),
    path("printers/<int:printer_id>/test/", views.test_printer, name="printer_test"),
]