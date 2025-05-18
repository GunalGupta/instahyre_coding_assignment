from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Case, When, Value, IntegerField, BooleanField, F


from .models import SpamReport, Contact
from auth_user.models import User
from .serializers import SpamReportSerializer, SearchResultSerializer

class MarkAsSpamView(generics.CreateAPIView):
    serializer_class = SpamReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user) 
        pass

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(
                {"message": f"Number {serializer.validated_data['phone_number']} marked as spam successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SearchByNameView(generics.ListAPIView):
    serializer_class = SearchResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        if not query or len(query) < 2:
            return [] 
        
        # 1. Search in registered Users
        users_qs = User.objects.filter(
            Q(name__istartswith=query) | Q(name__icontains=query)
        ).annotate(
            match_type=Case(
                When(name__istartswith=query, then=Value(1)), # Starts with
                default=Value(2), # Contains
                output_field=IntegerField(),
            ),
            is_actually_registered=Value(True, output_field=BooleanField()),
            contact_name=F('name') # User's own name is the contact_name
        ).values('id', 'contact_name', 'phone_number', 'email', 'match_type', 'is_actually_registered')

        # 2. Search in Contacts (non-registered or where name is different)
        contacts_qs = Contact.objects.filter(
            Q(name__istartswith=query) | Q(name__icontains=query)
        ).annotate(
            match_type=Case(
                When(name__istartswith=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            is_actually_registered=Case( # Checking if the contact is linked to a registered user
                When(registered_user__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ),
            contact_name=F('name') # Contact's saved name
        ).select_related('registered_user').values( # Select related for registered_user's email if needed
            'id', 'contact_name', 'phone_number', 'match_type', 'is_actually_registered', 'registered_user__email', 'registered_user_id'
        )
        
        results = []
        seen_phone_numbers_for_registered_users = set()

        # Process registered users first
        for user_data in users_qs.order_by('match_type', 'contact_name'):
            results.append({
                'name': user_data['contact_name'],
                'phone_number': user_data['phone_number'],
                'email_candidate': user_data['email'],
                'is_registered_user_instance_pk': user_data['id'],
                'is_registered_user': True,
                '_match_type': user_data['match_type']
            })
            seen_phone_numbers_for_registered_users.add(user_data['phone_number'])

        # Process contacts, avoiding duplicates if a registered user with the same phone was already added
        for contact_data in contacts_qs.order_by('match_type', 'contact_name'):
            is_primary_registered_user_record = contact_data['phone_number'] in seen_phone_numbers_for_registered_users and \
                                                contact_data['is_actually_registered'] and \
                                                User.objects.filter(pk=contact_data['registered_user_id'], name=contact_data['contact_name']).exists()

            if not is_primary_registered_user_record:
                results.append({
                    'name': contact_data['contact_name'],
                    'phone_number': contact_data['phone_number'],
                    'email_candidate': contact_data['registered_user__email'] if contact_data['is_actually_registered'] else None,
                    'is_registered_user_instance_pk': contact_data['registered_user_id'] if contact_data['is_actually_registered'] else None,
                    'is_registered_user': contact_data['is_actually_registered'],
                    '_match_type': contact_data['match_type']
                })
        
        final_results_map = {}
        for r in results:
            key = (r['name'], r['phone_number'])
            # Prioritize entries that are confirmed registered users
            if key not in final_results_map or \
               (r['is_registered_user'] and not final_results_map[key]['is_registered_user']) or \
               (r['_match_type'] < final_results_map[key]['_match_type']):
                final_results_map[key] = r
        
        # Sorting the results
        sorted_results = sorted(list(final_results_map.values()), key=lambda x: (x['_match_type'], x['name']))
        
        user_pks_to_fetch = {r['is_registered_user_instance_pk'] for r in sorted_results if r.get('is_registered_user_instance_pk')}
        user_instances_map = {user.pk: user for user in User.objects.filter(pk__in=user_pks_to_fetch)}

        for r_dict in sorted_results:
            if r_dict.get('is_registered_user_instance_pk'):
                r_dict['is_registered_user_instance'] = user_instances_map.get(r_dict['is_registered_user_instance_pk'])
            else:
                r_dict['is_registered_user_instance'] = None

        return sorted_results # List of dictionaries

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

class SearchByPhoneView(generics.ListAPIView):
    serializer_class = SearchResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        phone_query = self.request.query_params.get('phone', None)
        if not phone_query:
            return []
        
        normalized_phone_query = phone_query

        results_data = []

        # 1. Check for a registered user with this phone number
        try:
            registered_user = User.objects.get(phone_number=normalized_phone_query)
            results_data.append({
                'name': registered_user.name,
                'phone_number': registered_user.phone_number,
                'is_registered_user': True,
                'is_registered_user_instance': registered_user,
            })
            return results_data # Return immediately with only this user
        except User.DoesNotExist:
            pass

        # 2. If no registered user, search in Contacts for exact matches
        contacts_qs = Contact.objects.filter(phone_number=normalized_phone_query)
        
        for contact in contacts_qs:
            user_instance_for_contact = None
            if contact.registered_user: # If this contact is linked to a registered user
                user_instance_for_contact = contact.registered_user
            
            results_data.append({
                'name': contact.name, 
                'phone_number': contact.phone_number,
                'is_registered_user': bool(contact.registered_user),
                'is_registered_user_instance': user_instance_for_contact,
            })
        
        return results_data
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)