# attendance_eligibility_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views # Import Django's built-in auth views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('attendance.urls')), # Include URLs from your attendance app

    # Auth URLs (for login, logout)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    # You might want to add registration later, but for now, we'll use admin to create users.
]