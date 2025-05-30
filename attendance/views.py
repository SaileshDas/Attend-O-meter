# attendance/views.py
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import AcademicSessionForm, SubjectForm, ExamDateForm, AttendanceRecordForm, HolidayBulkForm
from .models import AcademicSession, Subject, AttendanceRecord, ExamDate, Holiday
from django.db import IntegrityError
from django.contrib import messages # For displaying messages to the user
from datetime import timedelta

# --- Helper function to count class days between two dates, considering holidays ---
def get_working_days_count(start_date, end_date, holidays_set):
    count = 0
    current = start_date
    while current <= end_date:
        # Check for Sunday (weekday() returns 6 for Sunday)
        if current.weekday() == 6: # Sunday
            current += timedelta(days=1) # Advance date
            continue # Skip to next iteration

        # Check for 1st and 3rd Saturday (weekday() returns 5 for Saturday)
        if current.weekday() == 5: # Saturday
            first_day_of_month_for_sat_check = current.replace(day=1)
            saturdays_in_month_so_far = 0
            temp_saturday_date = first_day_of_month_for_sat_check
            while temp_saturday_date <= current:
                if temp_saturday_date.weekday() == 5:
                    saturdays_in_month_so_far += 1
                temp_saturday_date += timedelta(days=1)
            
            if saturdays_in_month_so_far == 1 or saturdays_in_month_so_far == 3: # 1st or 3rd Saturday
                current += timedelta(days=1) # Advance date
                continue # Skip to next iteration

        # Check for declared holidays
        if current in holidays_set:
            current += timedelta(days=1) # Advance date
            continue # Skip to next iteration

        # If we reach here, it's a working day
        count += 1
        current += timedelta(days=1) # Always advance date at the end of the loop body for working days
    return count

# --- Dashboard View (Home Page) ---
@login_required
def dashboard_view(request):
    current_session = None
    try:
        current_session = AcademicSession.objects.get(user=request.user, is_current=True)
    except AcademicSession.DoesNotExist:
        messages.info(request, "Please set up your current academic session to get started.")
        return redirect('add_academic_session')

    subjects = Subject.objects.filter(session=current_session).order_by('name')
    # We will add more calculations here later for attendance status

    context = {
        'current_session': current_session,
        'subjects': subjects,
        'exam_dates': ExamDate.objects.filter(session=current_session).order_by('start_date'),
    }
    return render(request, 'attendance/dashboard.html', context)

# --- Academic Session Views ---
@login_required
def add_academic_session(request):
    if request.method == 'POST':
        form = AcademicSessionForm(request.POST)
        if form.is_valid():
            try:
                # Set all other sessions for this user to not current
                AcademicSession.objects.filter(user=request.user, is_current=True).update(is_current=False)

                session = form.save(commit=False)
                session.user = request.user
                session.is_current = True # Ensure new session is set as current
                session.save()
                messages.success(request, f"Academic Session '{session.name}' added and set as current!")
                return redirect('dashboard') # Redirect to the dashboard
            except IntegrityError:
                messages.error(request, "You already have a current session marked. Please unmark it or update it first, or choose a different name if creating a new one.")
                pass # Form will be re-rendered with errors if any
    else:
        form = AcademicSessionForm(initial={'is_current': True}) # Default to current for new sessions
    return render(request, 'attendance/add_academic_session.html', {'form': form})

@login_required
def update_academic_session(request, pk):
    session = get_object_or_404(AcademicSession, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AcademicSessionForm(request.POST, instance=session)
        if form.is_valid():
            try:
                # If this session is being set as current, unmark others
                if form.cleaned_data['is_current']:
                   AcademicSession.objects.filter(user=request.user, is_current=True).exclude(pk=session.pk).update(is_current=False)
                session.save()
                messages.success(request, f"Academic Session '{session.name}' updated successfully!")
                return redirect('dashboard')
            except IntegrityError:
                messages.error(request, "Failed to update session. Check for duplicate session names or current session conflicts.")
    else:
        form = AcademicSessionForm(instance=session)
    return render(request, 'attendance/update_academic_session.html', {'form': form, 'session': session})

@login_required
def academic_session_list(request):
    sessions = AcademicSession.objects.filter(user=request.user).order_by('-start_date')
    return render(request, 'attendance/academic_session_list.html', {'sessions': sessions})

# --- Subject Views ---
@login_required
def add_subject(request, session_pk):
    session = get_object_or_404(AcademicSession, pk=session_pk, user=request.user)
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.session = session # Assign the subject to the current session
            try:
                subject.save()
                messages.success(request, f"Subject '{subject.name}' added successfully to {session.name}!")
                return redirect('dashboard') # Or redirect to a subject list for the session
            except IntegrityError:
                messages.error(request, f"A subject with the name '{subject.name}' already exists in this session.")
    else:
        form = SubjectForm()
    context = {'form': form, 'session': session}
    return render(request, 'attendance/add_subject.html', context)

# Placeholder for future:
@login_required
def update_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk, session__user=request.user) # Ensure user owns the subject
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, f"Subject '{subject.name}' updated successfully!")
            return redirect('dashboard')
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'attendance/update_subject.html', {'form': form, 'subject': subject})

@login_required
def subject_detail(request, pk):
    subject = get_object_or_404(Subject, pk=pk, session__user=request.user)
    session = subject.session
    attendance_records = AttendanceRecord.objects.filter(subject=subject).order_by('date')

    total_conducted = sum(rec.classes_conducted for rec in attendance_records)
    total_attended = sum(rec.classes_attended for rec in attendance_records)

    current_percentage = (total_attended / total_conducted * 100) if total_conducted > 0 else 0

    eligibility_info = {}
    exam_dates = ExamDate.objects.filter(session=session).order_by('start_date')

    # Fetch all holidays for the current session once
    session_holidays = set(Holiday.objects.filter(session=session).values_list('date', flat=True))

    for exam in exam_dates:
        today = datetime.date.today() # Define today here inside the loop for each exam date projection

        if exam.start_date <= today:
            eligibility_info[exam.exam_type] = {
                'status': 'Exam Past',
                'detail': 'This exam date has already passed.',
                'total_projected_classes': total_conducted,
                'projected_attended': total_attended,
                'projected_percentage': current_percentage,
                'classes_to_attend_for_eligibility': 0,
                'classes_can_miss': 0,
            }
            continue

        # 1. Total projected classes until exam start date
        days_from_session_start_to_exam_end = exam.start_date - timedelta(days=1) # up to day before exam
        total_working_days_to_exam = get_working_days_count(session.start_date, days_from_session_start_to_exam_end, session_holidays)
        
        # Define average working days per week for scaling classes_per_week.
        # If your college has 1st/3rd Saturdays off, then a month has ~2 working Saturdays.
        # So average 5 weekdays + 2 working Saturdays / 4 = 5.5 working days per week.
        AVERAGE_WORKING_DAYS_PER_WEEK = 5.5 # Mon-Fri + average of 2 working Saturdays out of 4.

        # Calculate projected classes based on total working days
        total_projected_classes_until_exam = (total_working_days_to_exam / AVERAGE_WORKING_DAYS_PER_WEEK) * subject.classes_per_week
        total_projected_classes_until_exam = round(total_projected_classes_until_exam) # Round to nearest whole number

        # Ensure total_projected_classes_until_exam is at least equal to total_conducted
        # This prevents issues if the model for projection estimates fewer classes than have already occurred.
        total_projected_classes_until_exam = max(total_projected_classes_until_exam, total_conducted)

        if total_projected_classes_until_exam <= 0: # Recalculate if still zero/negative after max
             eligibility_info[exam.exam_type] = {
                'status': 'Not Applicable',
                'detail': 'Cannot project eligibility as no effective class days are expected before this exam date.',
                'total_projected_classes': 0,
                'classes_remaining_to_be_conducted': 0,
                'min_required_classes': 0,
                'classes_to_attend_for_eligibility': 0,
                'classes_can_miss': 0,
                'current_percentage': current_percentage,
                'projected_percentage_if_all_attended': 0,
            }
             continue


        # Classes remaining calculation:
        # Count working days from TODAY until exam start date
        # Use `today` for calculating remaining classes.
        
        # Ensure `today` is not after `days_from_session_start_to_exam_end` for `get_working_days_count`
        if today > days_from_session_start_to_exam_end:
            classes_remaining_to_be_conducted = 0
        else:
            classes_remaining_to_be_conducted_estimate = (get_working_days_count(today, days_from_session_start_to_exam_end, session_holidays) / AVERAGE_WORKING_DAYS_PER_WEEK) * subject.classes_per_week
            classes_remaining_to_be_conducted = max(0, round(classes_remaining_to_be_conducted_estimate))


        min_required_classes = (subject.minimum_attendance_percentage / 100) * total_projected_classes_until_exam
        min_required_classes = round(min_required_classes)

        projected_attended_if_all_attended = total_attended + classes_remaining_to_be_conducted
        projected_percentage_if_all_attended = (projected_attended_if_all_attended / total_projected_classes_until_exam * 100) if total_projected_classes_until_exam > 0 else 0


        status = ''
        detail = ''
        classes_to_attend_for_eligibility = 0
        classes_can_miss = 0

        if projected_percentage_if_all_attended < subject.minimum_attendance_percentage:
            status = 'Ineligible'
            detail = f"You cannot reach {subject.minimum_attendance_percentage:.2f}% attendance for this exam, even if you attend all {classes_remaining_to_be_conducted} remaining classes. Your max possible attendance will be {projected_percentage_if_all_attended:.2f}%."
            classes_to_attend_for_eligibility = classes_remaining_to_be_conducted # Essentially means they need to attend all
            classes_can_miss = 0
        else:
            classes_needed = max(0, min_required_classes - total_attended)

            if classes_needed > 0:
                status = 'Needs Attention'
                detail = f"You must attend at least {classes_needed} more classes to reach {subject.minimum_attendance_percentage:.2f}% eligibility. You can miss up to {classes_remaining_to_be_conducted - classes_needed} more classes."
                classes_to_attend_for_eligibility = classes_needed
                classes_can_miss = classes_remaining_to_be_conducted - classes_needed
            else:
                status = 'Good'
                
                max_missed_overall = total_projected_classes_until_exam - min_required_classes
                classes_already_missed = total_conducted - total_attended
                
                classes_can_miss = max(0, round(max_missed_overall - classes_already_missed))
                classes_can_miss = min(classes_can_miss, classes_remaining_to_be_conducted)

                if classes_can_miss == 0 and classes_remaining_to_be_conducted > 0:
                    status = 'Good (No Misses Left)'
                    detail = f"You are eligible, but you cannot miss any more of the remaining {classes_remaining_to_be_conducted} classes to maintain {subject.minimum_attendance_percentage:.2f}% eligibility for this exam."
                elif classes_can_miss == 0 and classes_remaining_to_be_conducted == 0:
                    status = 'Good (All Classes Done)'
                    detail = f"You are eligible. All projected classes for this exam are completed."
                else:
                    detail = f"You can afford to miss up to {classes_can_miss} more classes and still be eligible for this exam (reaching at least {subject.minimum_attendance_percentage:.2f}%)."
        
        eligibility_info[exam.exam_type] = {
            'status': status,
            'detail': detail,
            'total_projected_classes': total_projected_classes_until_exam,
            'classes_remaining_to_be_conducted': classes_remaining_to_be_conducted,
            'min_required_classes': min_required_classes,
            'classes_to_attend_for_eligibility': classes_to_attend_for_eligibility,
            'classes_can_miss': classes_can_miss,
            'current_percentage': current_percentage,
            'projected_percentage_if_all_attended': projected_percentage_if_all_attended,
        }

    context = {
        'subject': subject,
        'attendance_records': attendance_records,
        'total_conducted': total_conducted,
        'total_attended': total_attended,
        'current_percentage': current_percentage,
        'eligibility_info': eligibility_info,
    }
    return render(request, 'attendance/subject_detail.html', context)

# --- Attendance Record Views ---
@login_required
def add_attendance(request, subject_pk):
    subject = get_object_or_404(Subject, pk=subject_pk, session__user=request.user)
    if request.method == 'POST':
        form = AttendanceRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.subject = subject
            try:
                record.save()
                messages.success(request, f"Attendance for {subject.name} on {record.date} added.")
                return redirect('subject_detail', pk=subject.pk)
            except IntegrityError:
                messages.error(request, f"An attendance record for {subject.name} on {record.date} already exists.")
    else:
        # Set the initial date to today's date when the form is first displayed (GET request)
        form = AttendanceRecordForm(initial={'date': datetime.date.today()}) # <-- Change this line!
    context = {'form': form, 'subject': subject}
    return render(request, 'attendance/add_attendance.html', context)

# --- Exam Date Views ---
@login_required
def add_exam_date(request, session_pk):
    session = get_object_or_404(AcademicSession, pk=session_pk, user=request.user)
    if request.method == 'POST':
        form = ExamDateForm(request.POST)
        if form.is_valid():
            exam_date = form.save(commit=False)
            exam_date.session = session
            try:
                exam_date.save()
                messages.success(request, f"Exam date '{exam_date.exam_type}' added for {session.name}.")
                return redirect('dashboard')
            except IntegrityError:
                messages.error(request, f"An exam of type '{exam_date.exam_type}' already exists for this session.")
    else:
        form = ExamDateForm()
    context = {'form': form, 'session': session}
    return render(request, 'attendance/add_exam_date.html', context)

# We will add other views like list, update, delete as needed.

@login_required
def bulk_add_holidays(request):
    if request.method == 'POST':
        form = HolidayBulkForm(request.POST)
        if form.is_valid():
            session = form.cleaned_data['session']
            holiday_dates_text = form.cleaned_data.get('holiday_dates_text')
            
            holidays_added_count = 0
            errors = []

            # Process text input
            if holiday_dates_text:
                for line in holiday_dates_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        parts = line.split(' - ', 1) # Split only on the first ' - '
                        date_str = parts[0].strip()
                        holiday_name = parts[1].strip() if len(parts) > 1 else "Holiday" # Default name if not provided
                        
                        holiday_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        Holiday.objects.create(session=session, name=holiday_name, date=holiday_date)
                        holidays_added_count += 1
                    except ValueError:
                        errors.append(f"Invalid date format or entry: '{line}'. Please use YYYY-MM-DD.")
                    except IntegrityError:
                        errors.append(f"Holiday on {date_str} already exists for session '{session.name}'.")
                    except Exception as e:
                        errors.append(f"Error processing line '{line}': {e}")
            
            # (Optional: Add logic here to process CSV file if you include holiday_csv_file field)

            if holidays_added_count > 0:
                messages.success(request, f"Successfully added {holidays_added_count} holidays to session '{session.name}'.")
            if errors:
                for error_msg in errors:
                    messages.error(request, error_msg)
            
            if holidays_added_count > 0 and not errors:
                return redirect('dashboard') # Redirect to dashboard after successful bulk add
            
    else:
        form = HolidayBulkForm(initial={'session': AcademicSession.objects.filter(user=request.user, is_current=True).first()})
    
    context = {'form': form}
    return render(request, 'attendance/bulk_add_holidays.html', context)