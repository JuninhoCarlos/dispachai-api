from django.urls import include, path

from .views import LoginView, UserAPIView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="knox_login"),
    path("auth/", include("knox.urls")),
    path("auth/register/", UserAPIView.as_view(), name="user_register"),
]
