from django.urls import path, include

from .views import LoginView

urlpatterns = [
    path('login/', LoginView.as_view(), name='knox_login'),
    path('', include('knox.urls')),
]