from django.db import models
from django.conf import settings

class Contact(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='contacts',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255) 
    phone_number = models.CharField(max_length=20)
    
    registered_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='contact_entries', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner', 'phone_number')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone_number}) - owned by {self.owner.phone_number}"

class SpamReport(models.Model): 
    phone_number = models.CharField(max_length=20, db_index=True)

    # The user who reported this number as spam.
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='spam_reports_made',
        on_delete=models.CASCADE
    )

    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A condition so that a user cannot report the same number multiple times
        unique_together = ('phone_number', 'reported_by')
        ordering = ['-reported_at']

    def __str__(self):
        return f"{self.phone_number} reported by {self.reported_by.phone_number}"