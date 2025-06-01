# attendance_eligibility_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('attendance.urls')), # Include URLs from your attendance app

    # Auth URLs (for login, logout)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    # Removed next_page here so settings.LOGOUT_REDIRECT_URL = 'login' takes effect
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Password reset and other auth paths would need to be added explicitly here
    # if you're not using path('accounts/', include('django.contrib.auth.urls'))

    # Your custom signup URL is in attendance/urls.py, which is correct.
]