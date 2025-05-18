from django.urls import path
from .views import MarkAsSpamView, SearchByNameView, SearchByPhoneView

urlpatterns = [
    path('spam/mark/', MarkAsSpamView.as_view(), name='mark-spam'),
    path('search/name/', SearchByNameView.as_view(), name='search-by-name'),
    path('search/phone/', SearchByPhoneView.as_view(), name='search-by-phone'),
]