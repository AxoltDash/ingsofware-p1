from django.urls import path

from . import views

urlpatterns = [
    path('api/marcadores/', views.api_marcadores, name='api_marcadores'),
]
