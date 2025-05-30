# attendance/forms.py
import datetime
from django import forms
from .models import AcademicSession, Subject, AttendanceRecord, ExamDate, Holiday

class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'classes_per_week', 'minimum_attendance_percentage']

class ExamDateForm(forms.ModelForm):
    class Meta:
        model = ExamDate
        fields = ['exam_type', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['date', 'classes_conducted', 'classes_attended']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}), # <-- Change this line!
        }
        # The 'value' attribute is removed from here.
        # We will set the initial date in the view instead.

class HolidayBulkForm(forms.Form):
    session = forms.ModelChoiceField(queryset=AcademicSession.objects.all(), label="Academic Session")
    # Option 1: Paste multiple dates (one per line, or comma-separated)
    holiday_dates_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10}),
        label="Paste Holiday Dates (e.g., 'YYYY-MM-DD - Holiday Name' or just 'YYYY-MM-DD')",
        help_text="Enter one holiday per line. Format: YYYY-MM-DD (e.g., 2025-01-01) or YYYY-MM-DD - Holiday Name (e.g., 2025-01-26 - Republic Day).",
        required=False
    )
    # Option 2: Upload a CSV file
    # holiday_csv_file = forms.FileField(label="Upload CSV File", required=False)

    def clean(self):
        cleaned_data = super().clean()
        holiday_dates_text = cleaned_data.get('holiday_dates_text')
        # holiday_csv_file = cleaned_data.get('holiday_csv_file')

        if not holiday_dates_text: # and not holiday_csv_file:
            raise forms.ValidationError("Please provide holiday dates either by pasting text.")

        return cleaned_data