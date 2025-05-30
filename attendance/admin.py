# attendance/admin.py
from django.contrib import admin
from .models import (
    AcademicSession, Subject, AttendanceRecord, ExamDate, Holiday # Make sure Holiday is imported
)

# Register your models here.

# Academic Session Admin
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current', 'user')
    list_filter = ('is_current', 'start_date', 'end_date', 'user')
    search_fields = ('name',)

admin.site.register(AcademicSession, AcademicSessionAdmin)


# Subject Admin
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'minimum_attendance_percentage', 'classes_per_week')
    list_filter = ('session',)
    search_fields = ('name',)

admin.site.register(Subject, SubjectAdmin)


# Attendance Record Admin
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('subject', 'date', 'classes_conducted', 'classes_attended')
    list_filter = ('subject', 'date')
    search_fields = ('subject__name', 'date',)
    date_hierarchy = 'date'

admin.site.register(AttendanceRecord, AttendanceRecordAdmin)


# Exam Date Admin
class ExamDateAdmin(admin.ModelAdmin):
    list_display = ('session', 'exam_type', 'start_date', 'end_date')
    list_filter = ('session', 'exam_type')
    search_fields = ('exam_type',)

admin.site.register(ExamDate, ExamDateAdmin)


# Holiday Admin (This is the one we're focusing on)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'session') # Added 'session' to list_display
    list_filter = ('session', 'date')
    search_fields = ('name',)

admin.site.register(Holiday, HolidayAdmin) # Only one registration for Holiday, and pass HolidayAdmin