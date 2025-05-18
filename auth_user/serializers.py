from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ('phone_number', 'name', 'email', 'password', 'password_confirm')
        extra_kwargs = {
            'name': {'required': True},
            'phone_number': {'required': True},
        }

    def validate_phone_number(self, value):
        if not value.replace("+", "").isdigit() or not (10 <= len(value.replace("+", "")) <= 15):
             raise serializers.ValidationError(
                 "Invalid Phone Number, must be between 10 to 15 digits."
            )
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value

    def validate(self, attrs):
        # validation for password confirmation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            password=validated_data['password'],
            email=validated_data.get('email')
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(read_only=True) # Cannot change phone number via profile update

    class Meta:
        model = User
        fields = ('id', 'phone_number', 'name', 'email', 'date_joined')
        read_only_fields = ('id', 'phone_number', 'date_joined')

    def validate_email(self, value):
        user = self.instance 
        if value: 
            # Check if another user already has this email
            if User.objects.filter(email=value).exclude(pk=user.pk if user else None).exists():
                raise serializers.ValidationError("A user with this email address already exists.")
        return value