# attendance/views.py
import csv
from io import TextIOWrapper # Used to correctly read the uploaded file
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login # <-- Add this import if you want to auto-login users after signup
from django.urls import reverse
from .forms import AcademicSessionForm, SubjectForm, ExamDateForm, AttendanceRecordForm, HolidayBulkForm, HolidayUploadForm, SignUpForm
from .models import AcademicSession, Subject, AttendanceRecord, ExamDate, Holiday
from django.db import IntegrityError
from django.contrib import messages # For displaying messages to the user
from datetime import timedelta, datetime # <-- This import is correct for datetime.strptime()

# Helper function: get_working_days_count (Keep this as is, it's still useful for defining periods)
def get_working_days_count(start_date, end_date, holidays):
    """
    Calculates the number of working days (Mon-Fri + 1st/3rd Sat if applicable)
    between start_date and end_date (inclusive).
    """
    if start_date > end_date:
        return 0

    count = 0
    current_date = start_date
    
    while current_date <= end_date:
        if 0 <= current_date.weekday() <= 4: # Monday (0) to Friday (4)
            if current_date not in holidays:
                count += 1
        elif current_date.weekday() == 5: # Saturday (5)
            if (current_date.day - 1) // 7 in [0, 2]: # 1st or 3rd Saturday
                if current_date not in holidays:
                    count += 1
        current_date += timedelta(days=1)
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
    return render(request, 'attendance/academic_session_form.html', {'form': form})

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
    return render(request, 'attendance/academic_session_form.html', {'form': form, 'session': session})

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
    return render(request, 'attendance/subject_form.html', context)

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
    return render(request, 'attendance/subject_form.html', {'form': form, 'subject': subject})

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

    today = datetime.today().date() # Get current datetime, then extract date part

    # Define a minimum threshold for relying on observed historical data
    # If fewer than this many classes have been conducted, fall back to theoretical model
    MIN_CLASSES_FOR_HISTORICAL_PROJECTION = 5 # Adjust this number as needed (e.g., 10 or 15)

    for exam in exam_dates:
        # 0. Handle Exam Past scenario first
        if exam.start_date <= today:
            eligibility_info[exam.exam_type] = {
                'status': 'Exam Past',
                'detail': 'This exam date has already passed.',
                'total_projected_classes': total_conducted, 
                'projected_attended': total_attended,
                'projected_percentage': current_percentage,
                'classes_remaining_to_be_conducted': 0,
                'min_required_classes': 0,
                'classes_to_attend_for_eligibility': 0,
                'classes_can_miss': 0,
            }
            continue

        # Define the end date for total projections (day before exam starts)
        projection_end_date = exam.start_date - timedelta(days=1)

        # Handle edge case where session start date is after the projection end date
        if projection_end_date < session.start_date:
            total_projected_classes_until_exam = 0
            projection_method_detail = "Exam date before session start."
        else:
            # Calculate total working days from session start to exam date
            total_working_days_to_exam_end_date = get_working_days_count(session.start_date, projection_end_date, session_holidays)

            # Calculate working days elapsed from session start to today (inclusive)
            working_days_elapsed_till_today = get_working_days_count(session.start_date, today, session_holidays)

            # --- NEW PROJECTION LOGIC: Prioritize historical rate ---
            if total_conducted >= MIN_CLASSES_FOR_HISTORICAL_PROJECTION and working_days_elapsed_till_today > 0:
                # Calculate actual classes conducted per working day based on history
                actual_classes_per_working_day = total_conducted / working_days_elapsed_till_today
                
                # Project this rate over the total duration until the exam
                total_projected_classes_until_exam = actual_classes_per_working_day * total_working_days_to_exam_end_date
                total_projected_classes_until_exam = round(total_projected_classes_until_exam)
                projection_method_detail = "Based on observed historical class rate."
            else:
                # Fallback to the theoretical method if not enough history or no classes yet
                # This AVERAGE_WORKING_DAYS_PER_WEEK is only used if historical data isn't sufficient
                AVERAGE_WORKING_DAYS_PER_WEEK = 5.5 
                total_projected_classes_until_exam = (total_working_days_to_exam_end_date / AVERAGE_WORKING_DAYS_PER_WEEK) * subject.classes_per_week
                total_projected_classes_until_exam = round(total_projected_classes_until_exam)
                projection_method_detail = "Based on theoretical schedule (insufficient historical data)."

        # IMPORTANT: Ensure projected total is at least what's already conducted
        # This prevents scenarios where the projection model might estimate fewer classes than have already happened.
        total_projected_classes_until_exam = max(total_projected_classes_until_exam, total_conducted)
        
        # If no classes are projected (or somehow became 0 after max)
        if total_projected_classes_until_exam <= 0:
            eligibility_info[exam.exam_type] = {
                'status': 'Not Applicable',
                'detail': 'Cannot project eligibility as no effective class days are expected before this exam date or subject has no classes.',
                'total_projected_classes': 0,
                'classes_remaining_to_be_conducted': 0,
                'min_required_classes': 0,
                'classes_to_attend_for_eligibility': 0,
                'classes_can_miss': 0,
                'current_percentage': current_percentage,
                'projected_percentage_if_all_attended': 0,
            }
            continue

        # Calculate Classes Remaining to be Conducted (consistent with total projected)
        classes_remaining_to_be_conducted = max(0, total_projected_classes_until_exam - total_conducted)
        
        # Calculate Minimum Required Classes based on Total Projected
        min_required_classes = (subject.minimum_attendance_percentage / 100) * total_projected_classes_until_exam
        min_required_classes = round(min_required_classes)

        # Projected percentage if ALL remaining classes are attended
        projected_attended_if_all_attended = total_attended + classes_remaining_to_be_conducted
        projected_percentage_if_all_attended = (projected_attended_if_all_attended / total_projected_classes_until_exam * 100) if total_projected_classes_until_exam > 0 else 0

        status = ''
        detail = ''
        classes_to_attend_for_eligibility = 0
        classes_can_miss = 0

        # Determine Eligibility Status, Detail, and Classes to Attend/Miss
        if projected_percentage_if_all_attended < subject.minimum_attendance_percentage:
            status = 'Ineligible'
            detail = f"You cannot reach {subject.minimum_attendance_percentage:.2f}% attendance for this exam, even if you attend all {classes_remaining_to_be_conducted} remaining classes. Your max possible attendance will be {projected_percentage_if_all_attended:.2f}%."
            classes_to_attend_for_eligibility = classes_remaining_to_be_conducted 
            classes_can_miss = 0
        else:
            classes_needed = max(0, min_required_classes - total_attended)

            if classes_needed > 0: # Needs Attention: requires more classes to reach minimum
                status = 'Needs Attention'
                classes_to_attend_for_eligibility = classes_needed
                classes_can_miss = classes_remaining_to_be_conducted - classes_needed # Classes you can miss = Remaining classes - Classes needed to attend
                detail = f"You must attend at least {classes_needed} more classes to reach {subject.minimum_attendance_percentage:.2f}% eligibility. You can miss up to {classes_can_miss} more classes."
                
            else: # Good: Already met or exceeded minimum required attendance
                status = 'Good'
                classes_to_attend_for_eligibility = 0

                max_overall_misses_allowed = total_projected_classes_until_exam - min_required_classes
                classes_already_missed = total_conducted - total_attended
                
                classes_can_miss = max(0, max_overall_misses_allowed - classes_already_missed)
                classes_can_miss = min(classes_can_miss, classes_remaining_to_be_conducted) # Cap by actual remaining classes

                if classes_can_miss == 0 and classes_remaining_to_be_conducted > 0:
                    status = 'Good (No Misses Left)'
                    detail = f"You are eligible, but you cannot miss any more of the remaining {classes_remaining_to_be_conducted} classes to maintain {subject.minimum_attendance_percentage:.2f}% eligibility for this exam."
                elif classes_can_miss == 0 and classes_remaining_to_be_conducted == 0:
                    status = 'Good (All Classes Done)'
                    detail = f"You are eligible. All projected classes for this exam are completed."
                else:
                    detail = f"You can afford to miss up to {classes_can_miss} more classes and still be eligible for this exam (reaching at least {subject.minimum_attendance_percentage:.2f}%)."
        
        # Store all calculated info for the current exam, including projection method detail
        eligibility_info[exam.exam_type] = {
            'status': status,
            'detail': detail + (f" (Projection: {projection_method_detail})" if projection_method_detail else ""),
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

@login_required
def upload_holidays(request, session_id):
    # Ensure you are using AcademicSession here if that's your model name
    session = get_object_or_404(AcademicSession, pk=session_id, user=request.user)
    
    if request.method == 'POST':
        form = HolidayUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Use TextIOWrapper to read the uploaded file as text
            csv_file = TextIOWrapper(form.cleaned_data['csv_file'].file, encoding='utf-8')
            reader = csv.reader(csv_file)
            header_skipped = False
            holidays_added_count = 0
            errors = []

            for row_num, row in enumerate(reader):
                # Skip header row (first row) if present
                if row_num == 0 and not row[0].strip().replace('-', '').replace('/', '').isdigit(): # Simple heuristic: if first cell isn't numeric-looking, assume header
                    header_skipped = True
                    continue

                if not row or not row[0].strip(): # Skip empty rows or rows with empty first column
                    continue

                try:
                    date_str = row[0].strip()
                    holiday_name = row[1].strip() if len(row) > 1 else '' # Optional name

                    # Attempt to parse various date formats
                    holiday_date = None
                    # Ordered from most specific/least ambiguous to more common
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d'): 
                        try:
                            holiday_date = datetime.strptime(date_str, fmt).date()
                            break # Found a format, break the loop
                        except ValueError:
                            continue # Try next format
                    
                    if holiday_date is None:
                        errors.append(f"Row {row_num + 1}: Invalid date format '{date_str}'. Please use YYYY-MM-DD, DD-MM-YYYY, MM/DD/YYYY, DD/MM/YYYY, or YYYY/MM/DD.")
                        continue # Skip to next row

                    # Ensure holiday date is within session bounds (optional, but good practice)
                    if not (session.start_date <= holiday_date <= session.end_date):
                        errors.append(f"Row {row_num + 1}: Holiday date {holiday_date} is outside the session dates ({session.start_date} to {session.end_date}).")
                        continue # Skip to next row

                    # Create or get the holiday - IntegrityError handles unique_together
                    Holiday.objects.create(
                        session=session,
                        date=holiday_date,
                        name=holiday_name
                    )
                    holidays_added_count += 1

                except IntegrityError: # Catches unique_together constraint violation (duplicate date for session)
                    messages.warning(request, f"Holiday on {date_str} already exists for this session. Skipping row {row_num + 1}.")
                except IndexError: # Catches rows with not enough columns (e.g., just an empty row or a row with only a date and no name)
                    errors.append(f"Row {row_num + 1}: Malformed row. Expected at least a date column. Skipping.")
                except Exception as e:
                    # Catch any other unexpected errors during row processing
                    errors.append(f"Row {row_num + 1}: An unexpected error occurred: {e}")

            if holidays_added_count > 0:
                messages.success(request, f"Successfully added {holidays_added_count} holidays to session '{session.name}'.")
            if errors:
                for error in errors:
                    messages.error(request, error)
            
            return redirect('academic_session_list') # Redirect back to the list of sessions
        else:
            # If form is not valid (e.g., no file selected)
            messages.error(request, "Please correct the errors in the form.")
    else:
        # For GET requests, show an empty form
        form = HolidayUploadForm()
    
    context = {
        'form': form,
        'session': session,
    }
    return render(request, 'attendance/upload_holidays.html', context)

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
        form = AttendanceRecordForm(initial={'date': datetime.today().date()}) # CORRECTED: Get current datetime, then extract date part
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
                        
                        # CORRECTED LINE HERE:
                        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
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

# --- User Authentication Views ---
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # OPTIONAL: Log the user in immediately after signup
            # Uncomment the next line and make sure 'login' is imported from django.contrib.auth
            # login(request, user)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login') # Redirect to the login page
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})