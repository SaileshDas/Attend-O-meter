# attendance/forms.py
import datetime
from django import forms
from .models import AcademicSession, Subject, AttendanceRecord, ExamDate, Holiday

class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}), # For checkboxes
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
        fields = ['exam_type', 'start_date', 'end_date'] # Ensure 'end_date' is here if your model has it
        widgets = {
            'exam_type': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), # Add for end_date
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
    # For ModelChoiceField, use form-select for Bootstrap 5 styled dropdowns
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all(),
        label="Academic Session",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # For Textarea, add form-control
    holiday_dates_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
        label="Paste Holiday Dates (e.g., 'YYYY-MM-DD - Holiday Name' or just 'YYYY-MM-DD')",
        help_text="Enter one holiday per line. Format: YYYY-MM-DD (e.g., 2025-01-01) or YYYY-MM-DD - Holiday Name (e.g., 2025-01-26 - Republic Day).",
        required=False
    )
    # Option 2: Upload a CSV file (uncomment if you decide to implement)
    # holiday_csv_file = forms.FileField(label="Upload CSV File", required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        holiday_dates_text = cleaned_data.get('holiday_dates_text')
        # holiday_csv_file = cleaned_data.get('holiday_csv_file')

        if not holiday_dates_text: # and not holiday_csv_file:
            raise forms.ValidationError("Please provide holiday dates either by pasting text.")

        return cleaned_data
    
class HolidayUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Select a CSV file',
        help_text='Upload a CSV with holiday dates. Each row should contain a date in YYYY-MM-DD format (e.g., 2025-01-01, 2025-12-25,Christmas).',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )