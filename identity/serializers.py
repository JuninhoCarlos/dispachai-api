from django.contrib.auth import get_user_model
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["username", "email", "password", "is_staff", "is_superuser"]
        extra_kwargs = {
            "password": {
                "write_only": True
                },
            "is_staff": {
                "write_only": True
            }, 
            "is_superuser": {
                "write_only": True
            }
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = get_user_model()(**validated_data)
        user.set_password(password)
        user.save()
        return user