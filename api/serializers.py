from rest_framework import serializers
from .models import SpamReport, Contact
from auth_user.models import User
from .utils import get_spam_likelihood

class SpamReportSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=20, required=True)

    class Meta:
        model = SpamReport
        fields = ('phone_number',) 

    def validate_phone_number(self, value):
        value_cleaned = value.translate(str.maketrans('', '', ' ()-'))
        digits_only = value_cleaned.lstrip('+')
        if not digits_only.isdigit() or not (7 <= len(digits_only) <= 15):
            raise serializers.ValidationError("Invalid phone number format, must be between 7 to 15 digits.")
        return value

    def validate(self, data):
        request_user = self.context['request'].user
        phone_number_to_report = data['phone_number']

        if SpamReport.objects.filter(phone_number=phone_number_to_report, reported_by=request_user).exists():
            raise serializers.ValidationError(
                {"phone_number": "You already reported this number."}
            )
        
        if request_user.phone_number == phone_number_to_report:
            raise serializers.ValidationError(
                 {"detail": "You can't report your own number."} 
            )
            
        return data

    def create(self, validated_data):
        request_user = self.context['request'].user
        
        spam_report = SpamReport.objects.create(
            phone_number=validated_data['phone_number'],
            reported_by=request_user
        )
        return spam_report

class SearchResultSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone_number = serializers.CharField()
    spam_likelihood = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    # field for sorting/identification
    is_registered_user = serializers.BooleanField(read_only=True, default=False) 

    def get_spam_likelihood(self, obj):
        phone = None
        if isinstance(obj, User):
            phone = obj.phone_number
        elif isinstance(obj, Contact):
            phone = obj.phone_number
        elif isinstance(obj, dict):
            phone = obj.get('phone_number')
        
        if phone:
            return get_spam_likelihood(phone)
        return 0.0

    def get_email(self, obj):
        requesting_user = self.context['request'].user
        target_email = None
        target_is_registered_user = False
        target_user_instance = None

        if isinstance(obj, User):
            target_email = obj.email
            target_is_registered_user = True
            target_user_instance = obj
        elif isinstance(obj, Contact):
            # If the contact entry is linked to a registered user
            if obj.registered_user:
                target_email = obj.registered_user.email
                target_is_registered_user = True
                target_user_instance = obj.registered_user
        elif isinstance(obj, dict) and obj.get('is_registered_user_instance'):
            target_user_instance = obj.get('is_registered_user_instance')
            if target_user_instance:
                target_email = target_user_instance.email
                target_is_registered_user = True


        if target_is_registered_user and target_email and target_user_instance:
            # if the searching user exists in the contact list of the same.
            if Contact.objects.filter(owner=target_user_instance, phone_number=requesting_user.phone_number).exists():
                return target_email
        return None # Otherwise, do not show email