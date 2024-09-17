from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import RedirectView


urlpatterns = [
    path('', views.index, name='index'),
    path('all_dict', views.all_dict, name='all_dict'),
    path('training', views.training, name='training'),
    path('reward', views.reward, name='reward'),

    path('card/<str:dict_name>/<str:u_eng_word>/', views.card, name='card'),
    path('edit_card/<str:dict_name>/<int:word_id>/', views.edit_card, name='edit_card'),
    path('delete_card/<int:word_id>/', views.delete_card, name='delete_card'),

    path('get-oxf-data/<str:u_eng_word>/', views.get_oxf_data, name='get_oxf_data'),

    path('dictionaries', views.engage_dictionaries, name='engage_dictionaries'),

    path('dict/<slug:dict_name>/', views.dictionary, name='dictionary'),
    path('add_dictionary', views.add_dictionary, name='add_dictionary'),
    path('delete_dictionary/<int:dict_id>/', views.delete_dictionary, name='delete_dictionary'),

    path('add_word', views.add_word_modal, name='add_word_modal'),

    path('', include('django.contrib.auth.urls')),
    path('index.html', RedirectView.as_view(url='/')),
    path('get_started.html', views.get_started, name='get_started'),
    path('about.html', views.about, name='about'),

    path('register/', views.register, name='register'),

    path('register_done/', views.register_done, name='register_done'),  # ВРЕМЕННОЕ РЕШЕНИЕ

    path('<str:user>/profile_dashboard/', views.profile_dashboard, name='profile_dashboard'),

    path('level/<int:lvl>/', views.level_view, name='level'),

    path('<str:user>/profile_settings/', views.profile_settings, name='profile_settings'),
    path('<str:user>/profile_edit/', views.profile_edit, name='profile_edit'),
    path('<str:user>/profile_delete/', views.profile_delete, name='profile_delete'),
    path('error404/', views.error404, name='error404'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
