from django.db.models import Count
from .models import SpamReport

def get_spam_likelihood(phone_number):
    if not phone_number:
        return 0
    
    report_count = SpamReport.objects.filter(phone_number=phone_number).count()

    MAX_REPORTS_FOR_HIGH_SPAM = 10 # If 10 or more reports, consider it high likelihood
    
    if report_count == 0:
        return 0.0
    elif report_count >= MAX_REPORTS_FOR_HIGH_SPAM:
        return 100.0
    else:
        return round((report_count / MAX_REPORTS_FOR_HIGH_SPAM) * 100, 2)

def normalize_phone_number_for_search(phone_number_str):
    if not phone_number_str:
        return ""
    normalized = ''.join(filter(lambda char: char.isdigit() or char == '+', phone_number_str))
    if normalized.startswith('+'):
        if not normalized[1:].isdigit(): 
            return phone_number_str
    elif not normalized.isdigit():
        return phone_number_str
    
    return normalized