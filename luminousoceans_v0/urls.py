"""
URL configuration for luminousoceans_v0 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import re_path, path
from .views import home, login_view, register_view, user_profile
from plataforma.views import semilla, capital_semilla_chat

urlpatterns = [
    path('capital-semilla-chat/', capital_semilla_chat, name='capital-semilla-chat'),
    path('plataforma/', semilla, name='plataforma'),
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('user-profile/', user_profile, name='user-profile'),
    path('admin/', admin.site.urls),
]
