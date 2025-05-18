import random
from faker import Faker
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.hashers import make_password

from auth_user.models import User
from api.models import Contact, SpamReport

# Initialize Faker
fake = Faker('en_IN') # 'en_IN' = for Indian names/numbers

# Configuration for data population
NUM_USERS = 20
NUM_CONTACTS_PER_USER_MIN = 5
NUM_CONTACTS_PER_USER_MAX = 30
PERCENT_USERS_WITH_CONTACTS = 0.8
PERCENT_CONTACTS_ARE_REGISTERED_USERS = 0.3
NUM_SPAM_REPORTS_GLOBAL = 50
PERCENT_SPAM_REPORTS_ON_REGISTERED_USERS = 0.2

class Command(BaseCommand):
    help = 'Populates the database with random sample data for CustomUsers, Contacts, and spam reports.'

    @transaction.atomic # Ensure all or nothing operation
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Start generating data for population...'))

        # ---Start: To Clear existing data ---
        self.stdout.write('Clearing existing data (Users, Contacts, SpamReports)...')
        SpamReport.objects.all().delete()
        Contact.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete() # Keep superusers
        self.stdout.write(self.style.WARNING('Existing data cleared.'))
        # --- End: Clear existing data ---

        created_users = []
        all_phone_numbers_in_system = set() # To keep track of all numbers for spam reporting

        # 1. To Create our X Users
        self.stdout.write(f'Creating {NUM_USERS} users...')
        for i in range(NUM_USERS):
            name = fake.name()
            # Setting unique phone numbers for registration
            phone_number = self._generate_unique_phone_number(all_phone_numbers_in_system, is_registered=True)
            all_phone_numbers_in_system.add(phone_number)

            email = None
            if random.random() < 0.7:
                # Setting unique email
                temp_email = fake.unique.email()
                while User.objects.filter(email=temp_email).exists():
                    temp_email = fake.unique.email()
                email = temp_email
            
            password = "password123" # simple password for every registered user under fake data

            try:
                user = User.objects.create_user(
                    phone_number=phone_number,
                    name=name,
                    email=email,
                    password=password
                )
                created_users.append(user)
                if (i + 1) % (NUM_USERS // 10 or 1) == 0:
                     self.stdout.write(f'{i+1}/{NUM_USERS} users created...')
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error creating user {name} ({phone_number}): {e}"))
        self.stdout.write(self.style.SUCCESS(f'{len(created_users)} users created successfully.'))


        # 2. Create Contacts for Users
        self.stdout.write('Creating contacts...')
        users_with_contacts_count = 0
        total_contacts_created = 0
        
        # Random picking
        users_for_contacts = random.sample(created_users, int(len(created_users) * PERCENT_USERS_WITH_CONTACTS))

        for owner_user in users_for_contacts:
            num_contacts_for_this_user = random.randint(NUM_CONTACTS_PER_USER_MIN, NUM_CONTACTS_PER_USER_MAX)
            contacts_for_this_user_created = 0
            owner_contact_phone_numbers = set()

            for _ in range(num_contacts_for_this_user):
                contact_name = fake.name()
                contact_is_registered_user = None
                if created_users and random.random() < PERCENT_CONTACTS_ARE_REGISTERED_USERS:
                    contact_is_registered_user = random.choice(created_users)
                    # Avoiding the condition where the contact is the same as the owner
                    if contact_is_registered_user == owner_user or \
                       contact_is_registered_user.phone_number in owner_contact_phone_numbers:
                        contact_is_registered_user = None

                if contact_is_registered_user:
                    contact_phone_number = contact_is_registered_user.phone_number
                else:
                    contact_phone_number = self._generate_unique_phone_number(all_phone_numbers_in_system, is_contact_number=True)
                
                all_phone_numbers_in_system.add(contact_phone_number)

                # Putting in a check to avoid duplicates in the same user's contacts
                if contact_phone_number in owner_contact_phone_numbers:
                    continue 

                try:
                    Contact.objects.create(
                        owner=owner_user,
                        name=contact_name,
                        phone_number=contact_phone_number,
                        registered_user=contact_is_registered_user # Link if it's a registered user
                    )
                    owner_contact_phone_numbers.add(contact_phone_number)
                    contacts_for_this_user_created += 1
                    total_contacts_created += 1
                    
                except Exception as e: # Catch IntegrityError 
                    self.stderr.write(self.style.ERROR(f"Error creating contact for {owner_user}: {e}"))
            
            if contacts_for_this_user_created > 0:
                users_with_contacts_count +=1
            # self.stdout.write(f'  {contacts_for_this_user_created} contacts for user {owner_user.phone_number}.')
        self.stdout.write(self.style.SUCCESS(f'{total_contacts_created} contacts created for {users_with_contacts_count} users in global database.'))


        # 3. Create Spam Reports
        self.stdout.write(f'Creating {NUM_SPAM_REPORTS_GLOBAL} spam reports...')
        spam_reports_created = 0
        if not created_users or not all_phone_numbers_in_system:
            self.stdout.write(self.style.WARNING('No users or phone numbers available to create spam reports.'))
        else:
            # Create a list of unique phone numbers to be reported
            potential_spam_numbers = list(all_phone_numbers_in_system)
            
            for _ in range(NUM_SPAM_REPORTS_GLOBAL):
                if not potential_spam_numbers: break # No more numbers to report

                number_to_report = random.choice(potential_spam_numbers)
                reporter = random.choice(created_users)

                # Avoiding the condition where user reporting their own number/same number multiple times
                if reporter.phone_number == number_to_report or \
                   SpamReport.objects.filter(phone_number=number_to_report, reported_by=reporter).exists():
                    continue

                try:
                    SpamReport.objects.create(
                        phone_number=number_to_report,
                        reported_by=reporter
                    )
                    spam_reports_created += 1
                except Exception as e:
                     self.stderr.write(self.style.ERROR(f"Error creating spam report by {reporter} for {number_to_report}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'{spam_reports_created} spam reports created.'))
        self.stdout.write(self.style.SUCCESS('Data population completed!'))

    def _generate_unique_phone_number(self, existing_numbers_set, is_registered=False, is_contact_number=False):
        """
        Generates a unique phone number.
        """
        max_attempts = 100 # Prevent infinite loop
        for _ in range(max_attempts):
            if random.random() < 0.5: # Some international-like numbers
                 num_part = f"{random.randint(100000000, 999999999)}" # 9 digits
                 phone = f"+{random.randint(1, 99)}{num_part}" 
            else: # Some local-like numbers
                 phone = f"0{random.randint(6,9)}{random.randint(100000000,999999999)}"[-10:] # 10 digits
            
            if phone not in existing_numbers_set:
                if is_registered:
                    if not User.objects.filter(phone_number=phone).exists():
                        return phone
                elif is_contact_number:
                    return phone 
                else:
                    return phone
        
        # Fallback if many attempts fail
        return fake.unique.numerify(text='##########') # Generic 10-digits