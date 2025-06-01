# attendance/forms.py
import datetime
from django import forms
from .models import AcademicSession, Subject, AttendanceRecord, ExamDate, Holiday

# ADD THIS IMPORT:
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User # You might also need to import User model


class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'classes_per_week', 'minimum_attendance_percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'classes_per_week': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_attendance_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ExamDateForm(forms.ModelForm):
    class Meta:
        model = ExamDate
        fields = ['exam_type', 'start_date', 'end_date']
        widgets = {
            'exam_type': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['date', 'classes_conducted', 'classes_attended']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'classes_conducted': forms.NumberInput(attrs={'class': 'form-control'}),
            'classes_attended': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class HolidayBulkForm(forms.Form):
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all(),
        label="Academic Session",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    holiday_dates_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
        label="Paste Holiday Dates (e.g., 'YYYY-MM-DD - Holiday Name' or just 'YYYY-MM-DD')",
        help_text="Enter one holiday per line. Format: YYYY-MM-DD (e.g., 2025-01-01) or YYYY-MM-DD - Holiday Name (e.g., 2025-01-26 - Republic Day).",
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        holiday_dates_text = cleaned_data.get('holiday_dates_text')

        if not holiday_dates_text:
            raise forms.ValidationError("Please provide holiday dates either by pasting text.")

        return cleaned_data
    
class HolidayUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Select a CSV file',
        help_text='Upload a CSV with holiday dates. Each row should contain a date in YYYY-MM-DD format (e.g., 2025-01-01, 2025-12-25,Christmas).',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )

# --- ADD THIS NEW CLASS FOR SIGNUP ---
class SignUpForm(UserCreationForm):
    class Meta:
        model = User # Use Django's built-in User model
        fields = ('username', 'email') # You can add more fields if your User model has them
        # If you want to use existing widgets for username, you can specify them here:
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    # Optional: Add a clean_email method to ensure email is unique
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email