from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("email", "username", "password", "first_name", "last_name")
        extra_kwargs = {"username": {"required": False}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "date_joined",
            # Needed so the frontend can hide admin UI from non-admin users.
            "is_staff",
            "is_superuser",
        )
        read_only_fields = ("id", "email", "date_joined", "is_staff", "is_superuser")


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name")


class AdminItemOwnerSerializer(serializers.ModelSerializer):
    """Owner summary for staff item list (includes email)."""

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name")


class AdminUserSerializer(serializers.ModelSerializer):
    """Staff-only list/detail for user management."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "date_joined",
            "is_active",
            "is_staff",
            "is_superuser",
        )
        read_only_fields = fields


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Only `is_active` may be changed (ban / unban)."""

    class Meta:
        model = User
        fields = ("is_active",)
