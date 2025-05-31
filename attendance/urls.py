# attendance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),

    # Academic Session URLs
    path('session/add/', views.add_academic_session, name='add_academic_session'),
    path('session/update/<int:pk>/', views.update_academic_session, name='update_academic_session'),
    path('sessions/', views.academic_session_list, name='academic_session_list'),
    # You might want to add a detail view for AcademicSession if you don't have one
    # This is the path that `upload_holidays` will redirect to after successful upload
    # Assuming 'academic_session_list' is where you want to redirect, or create an 'academic_session_detail'
    # For now, let's assume you'll redirect to academic_session_list or we'll add a detail view.
    # If you have a view like views.academic_session_detail (for a single session by its PK), uncomment/add this:
    # path('session/<int:pk>/detail/', views.academic_session_detail, name='academic_session_detail'),


    # Subject URLs
    path('session/<int:session_pk>/subject/add/', views.add_subject, name='add_subject'),
    path('subject/<int:pk>/', views.subject_detail, name='subject_detail'),
    path('subject/update/<int:pk>/', views.update_subject, name='update_subject'),


    # Attendance Record URLs
    path('subject/<int:subject_pk>/attendance/add/', views.add_attendance, name='add_attendance'),

    # Exam Date URLs
    path('session/<int:session_pk>/examdate/add/', views.add_exam_date, name='add_exam_date'),

    # Old bulk add holidays path (leave for now, but note it's separate from our new upload)
    path('holidays/bulk-add/', views.bulk_add_holidays, name='bulk_add_holidays'),

    # ADD THIS NEW URL PATTERN FOR UPLOADING HOLIDAYS PER SESSION
    path('session/<int:session_id>/upload_holidays/', views.upload_holidays, name='upload_holidays'),
]