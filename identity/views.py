from django.contrib.auth import login

from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.generics import CreateAPIView
from knox.views import LoginView as KnoxLoginView
from drf_spectacular.utils import extend_schema

from .serializers import UserSerializer 
from .permissions import IsSuperUser

class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)

class UserAPIView(CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]
    queryset = get_user_model().objects.all() 
