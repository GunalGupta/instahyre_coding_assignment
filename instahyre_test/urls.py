from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('auth_user.urls')),  # URLs for authentication and user management
    path('api/', include('api.urls')),        # URLs for the other API endpoints
]
