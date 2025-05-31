from django.contrib import admin
from django.urls import path
from . import views  # Adjust this if your views are in a different app/module

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),

    path('chat/', views.chat_home, name='chat_home'),
    path('send_message/', views.send_message, name='send_message'),
    path('get_messages/', views.get_messages, name='get_messages'),

    path('create_group/', views.createGroup, name='create_group'),
    path('add_to_group/', views.add_to_group, name='add_to_group'),
]
