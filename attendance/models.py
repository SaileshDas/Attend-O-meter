# attendance/models.py
from django.db import models
from django.contrib.auth import get_user_model # To link data to specific users

User = get_user_model()

# --- AcademicSession Model ---
class AcademicSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='academic_sessions')
    name = models.CharField(max_length=100, help_text="e.g., Odd Semester 2024-2025")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, help_text="Is this the active session for the user?")

    def __str__(self):
        return f"{self.name} ({self.start_date.year}-{self.end_date.year})"

    class Meta:
        # Ensures a user can only have one current session at a time
        unique_together = ('user', 'is_current')
        constraints = [
            models.UniqueConstraint(fields=['user'], condition=models.Q(is_current=True), name='unique_current_session')
        ]


# --- Subject Model ---
class Subject(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, null=True, help_text="e.g., CS301")
    classes_per_week = models.PositiveIntegerField(
        help_text="Number of classes (lectures/tutorials) for this subject per week."
    )
    minimum_attendance_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=75.00,
        help_text="Minimum attendance required (e.g., 75.00 for 75%)"
    )

    def __str__(self):
        return f"{self.name} ({self.code or 'N/A'}) - {self.session.name}"

    class Meta:
        unique_together = ('session', 'name') # A subject name should be unique within a session


# --- AttendanceRecord Model ---
class AttendanceRecord(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    classes_conducted = models.PositiveIntegerField(
        default=1, help_text="Number of classes conducted on this date for the subject."
    )
    classes_attended = models.PositiveIntegerField(
        default=0, help_text="Number of classes attended by the student on this date for the subject."
    )

    def __str__(self):
        return f"{self.subject.name} - {self.date}: {self.classes_attended}/{self.classes_conducted}"

    class Meta:
        unique_together = ('subject', 'date') # Only one attendance record per subject per day
        ordering = ['-date'] # Order records by newest first

# --- ExamDate Model ---
class ExamDate(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='exam_dates')
    exam_type = models.CharField(
        max_length=100,
        help_text="e.g., Mid-Semester Exam 1, Internal Test 2, End-Semester Exam"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Optional: End date of the exam period") # <--- ADD THIS LINE

    def __str__(self):
        return f"{self.session.name} - {self.exam_type} starts on {self.start_date}"

    class Meta:
        unique_together = ('session', 'exam_type')
        ordering = ['start_date']

# --- Holiday Model ---
class Holiday(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    # ADD THIS NEW FIELD:
    name = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        # ADD THIS UNIQUE CONSTRAINT:
        unique_together = ('session', 'date')
        ordering = ['date'] # Optional: Keeps holidays sorted by date

    def __str__(self):
        # Update the __str__ method to include the name
        return f"{self.date} - {self.name or 'Holiday'} ({self.session.name})"