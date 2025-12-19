"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path
from examiner.views import start_interview, submit_answer, landing ,chat,upload_pdf

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name='landing'), # Root URL shows Landing Page
    path('chat/',chat, name='chat'), 
    path('api/start/', start_interview),
    path('api/answer/', submit_answer),
   path('api/upload/', upload_pdf, name='upload_pdf'),

]


