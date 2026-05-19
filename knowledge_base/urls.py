from django.urls import path
from .import views


urlpatterns = [
    path('compatability_manipulation_page', views.compatability_manipulation_page, name='compatability_manipulation_page'),
    path('ajax_get_parts', views.ajax_get_parts, name='ajax_get_parts'),
    # path('ajax_get_models', views.ajax_get_models, name='ajax_get_models'),
    path('ajax_get_part_details', views.ajax_get_part_details, name='ajax_get_part_details'),
    
    path('ajax_get_part_compatibility', views.ajax_get_part_compatibility, name='ajax_get_part_compatibility'),
    path('ajax_search_models', views.ajax_search_models, name='ajax_search_models'),
    path('ajax_search_models_1', views.ajax_search_models_1, name='ajax_search_models_1'),
    
    path('ajax_save_compatibility', views.ajax_save_compatibility, name='ajax_save_compatibility'),
    path('ajax_get_transmission_options', views.ajax_get_transmission_options, name='ajax_get_transmission_options'),

    path('ajax_add_car_model', views.ajax_add_car_model, name='ajax_add_car_model'),
    
    path('ajax_navigate_part', views.ajax_navigate_part, name='ajax_navigate_part'),
    
    path('get_part_and_compatable_models', views.get_part_and_compatable_models, name='get_part_and_compatable_models'),
    path('get_model_and_compatable_parts', views.get_model_and_compatable_parts, name='get_model_and_compatable_parts'),
    
    path('add_to_cart_from_look_up', views.add_to_cart_from_look_up, name='add_to_cart_from_look_up'),
]