from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from attendance.forms import AttendanceActionForm, BreakActionForm
from attendance.models import Attendance, DeviceLog, BreakLog
from attendance.utils import haversine_meters
from core.models import OfficeSettings


def _get_office_settings():
    # Single settings row expected; fallback values if not configured.
    try:
        return OfficeSettings.objects.order_by('-updated_at').first()
    except Exception:
        return None


def _get_client_ip(request):
    # Best-effort; when behind proxy, add appropriate configuration in Django.
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _is_admin_user(user):
    return user.is_superuser or getattr(user, 'role', None) == 'admin'


def _log_device(request, user, note=''):
    ua = request.META.get('HTTP_USER_AGENT', '')[:500]
    ip = _get_client_ip(request)
    # Lightweight fingerprint: user agent + (ip prefix)
    ua_sig = (ua[:200] + '|' + '.'.join(ip.split('.')[:2])).encode('utf-8', errors='ignore')
    import hashlib

    fingerprint = hashlib.sha256(ua_sig).hexdigest()
    DeviceLog.objects.create(
        user=user,
        user_agent=ua,
        ip_address=ip,
        device_fingerprint=fingerprint,
        note=note,
    )


@login_required
def check_in(request):
    if request.method != 'POST':
        return render(request, 'attendance/check_in.html')

    form = AttendanceActionForm(request.POST)
    if not form.is_valid():
        return render(request, 'attendance/check_in.html', {'form_errors': 'Invalid location.'})

    lat = form.cleaned_data['latitude']
    lon = form.cleaned_data['longitude']

    now = timezone.localtime(timezone.now())
    today = now.date()

    # Geo validation
    settings = _get_office_settings()
    if settings and settings.office_latitude is not None and settings.office_longitude is not None:
        radius = settings.radius_meters or 100
        # dist = haversine_meters(lat, lon, settings.office_latitude, settings.office_longitude)
        print("USER LAT:", lat)
        print("USER LON:", lon)

        print("OFFICE LAT:", settings.office_latitude)
        print("OFFICE LON:", settings.office_longitude)

        dist = haversine_meters(
            lat,
            lon,
            settings.office_latitude,
            settings.office_longitude,
        )

        print("DISTANCE:", dist)
        print("RADIUS:", radius)
        # GPS/Wi-Fi positioning can be noisy (often 30-300m indoors). Allow substantial tolerance.
        # If you need stricter behavior, increase radius_meters instead of removing this buffer.
        tolerance_m = 2000
        # Server-side accuracy validation (best-effort): if client provided accuracy, prefer it.
        client_acc = form.cleaned_data.get('accuracy') if 'form' in locals() else None
        if client_acc is not None:
            # If the reported accuracy is very low (large number), treat as unreliable and deny.
            if client_acc > 2000:
                return render(request, 'attendance/check_in.html', {'form_errors': 'Location accuracy is too low. Use GPS and retry.'})

        if dist > (radius + tolerance_m):
            return render(
                request,
                'attendance/check_in.html',
                {
                    'form_errors': 'You are outside the office premises. Attendance denied.',
                },
            )


    # Prevent duplicate check-in
    if Attendance.objects.filter(intern=request.user, date=today, check_in_time__isnull=False).exists():
        return render(
            request,
            'attendance/check_in.html',
            {'form_errors': 'You have already checked in today.'},
        )

    Attendance.objects.create(
        intern=request.user,
        date=today,
        check_in_time=now.time(),
        status=Attendance.Status.PRESENT,
        is_late=False,
        total_working_hours=0,
        checked_in_at=now,
    )

    # Late detection (simple default: 10:00 is considered on-time unless settings later extends)
    # If you want configurable late time, store it in OfficeSettings.
    from datetime import datetime, time

    late_threshold = timezone.make_aware(
        datetime.combine(today, time(hour=10, minute=0))
    )

    attendance = Attendance.objects.get(intern=request.user, date=today)

    check_in_dt = timezone.make_aware(
        datetime.combine(today, attendance.check_in_time)
    )

    if check_in_dt > late_threshold:
        attendance.is_late = True
        attendance.save(update_fields=['is_late'])

    _log_device(request, request.user, note='check-in')
    return HttpResponseRedirect(reverse('attendance:check_in'))


@login_required
def check_out(request):
    if request.method != 'POST':
        return render(request, 'attendance/check_out.html')

    form = AttendanceActionForm(request.POST)
    if not form.is_valid():
        return render(request, 'attendance/check_out.html', {'form_errors': 'Invalid location.'})

    lat = form.cleaned_data['latitude']
    lon = form.cleaned_data['longitude']

    now = timezone.localtime(timezone.now())
    today = now.date()

    settings = _get_office_settings()
    if settings and settings.office_latitude is not None and settings.office_longitude is not None:
        radius = settings.radius_meters or 100
        dist = haversine_meters(lat, lon, settings.office_latitude, settings.office_longitude)
        tolerance_m = 100
        client_acc = form.cleaned_data.get('accuracy') if 'form' in locals() else None
        if client_acc is not None and client_acc > 2000:
            return render(request, 'attendance/check_out.html', {'form_errors': 'Location accuracy is too low. Use GPS and retry.'})

        if dist > (radius + tolerance_m):
            return render(
                request,
                'attendance/check_out.html',
                {
                    'form_errors': 'You are outside the office premises. Attendance denied.',
                },
            )


    try:
        attendance = Attendance.objects.get(intern=request.user, date=today)
    except Attendance.DoesNotExist:
        return render(
            request,
            'attendance/check_out.html',
            {'form_errors': 'Please check in before checking out.'},
        )

    if attendance.check_in_time is None:
        return render(
            request,
            'attendance/check_out.html',
            {'form_errors': 'Please check in before checking out.'},
        )

    if attendance.check_out_time is not None:
        return render(
            request,
            'attendance/check_out.html',
            {'form_errors': 'You have already checked out today.'},
        )

    attendance.check_out_time = now.time()
    attendance.checked_out_at = now

    # Compute total working hours
    from datetime import datetime

    check_in_dt = datetime.combine(today, attendance.check_in_time)
    check_out_dt = datetime.combine(today, attendance.check_out_time)
    total_seconds = max((check_out_dt - check_in_dt).total_seconds(), 0)
    attendance.total_working_hours = total_seconds / 3600.0

    attendance.status = Attendance.Status.PRESENT
    attendance.save(update_fields=['check_out_time', 'total_working_hours', 'status', 'checked_out_at'])

    _log_device(request, request.user, note='check-out')
    return HttpResponseRedirect(reverse('attendance:check_out'))


@login_required
def history(request):
    now = timezone.localtime(timezone.now())
    attendances = Attendance.objects.filter(intern=request.user).order_by('-date')
    total_days = attendances.count()
    late_count = attendances.filter(is_late=True).count()
    total_hours = sum(float(a.total_working_hours) for a in attendances)
    avg_hours = total_hours / total_days if total_days else 0
    total_break_minutes = sum(a.total_break_minutes for a in attendances)
    break_hours = total_break_minutes / 60.0 if total_break_minutes else 0

    return render(
        request,
        'attendance/history.html',
        {
            'attendances': attendances,
            'total_days': total_days,
            'late_count': late_count,
            'avg_hours': avg_hours,
            'break_hours': break_hours,
        },
    )


@login_required
def export_csv(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Not allowed')

    import csv
    from django.http import HttpResponse

    date_from = request.GET.get('from')
    date_to = request.GET.get('to')

    qs = Attendance.objects.all().select_related('intern')
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="hajiri_attendance.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ['intern', 'date', 'check_in', 'check_out', 'status', 'late', 'late_minutes', 'total_hours']
    )
    for a in qs.order_by('date'):
        writer.writerow(
            [
                a.intern.username,
                a.date.isoformat(),
                a.check_in_time.strftime('%H:%M:%S') if a.check_in_time else '',
                a.check_out_time.strftime('%H:%M:%S') if a.check_out_time else '',
                a.status,
                'YES' if a.is_late else 'NO',
                0,
                f"{a.total_working_hours:.2f}",
            ]
        )
    return response


@login_required
def break_action(request):
    """Handle break start/end actions."""
    if request.method != 'POST':
        now = timezone.localtime(timezone.now())
        today = now.date()
        
        try:
            attendance = Attendance.objects.get(intern=request.user, date=today)
        except Attendance.DoesNotExist:
            attendance = None
        
        active_break = BreakLog.objects.filter(
            user=request.user,
            date=today,
            end_time__isnull=True
        ).first()
        
        return render(request, 'attendance/break_action.html', {
            'attendance': attendance,
            'active_break': active_break,
        })
    
    form = BreakActionForm(request.POST)
    if not form.is_valid():
        return render(request, 'attendance/break_action.html', {
            'form_errors': 'Invalid request.'
        })
    
    action = form.cleaned_data['action']
    now = timezone.localtime(timezone.now())
    today = now.date()
    
    if action == 'start':
        # Get geolocation
        lat = form.cleaned_data.get('latitude')
        lon = form.cleaned_data.get('longitude')
        
        # Check if already on break
        active_break = BreakLog.objects.filter(
            user=request.user,
            date=today,
            end_time__isnull=True
        ).first()
        
        if active_break:
            return render(request, 'attendance/break_action.html', {
                'form_errors': 'You are already on break.'
            })
        
        # Create break log
        BreakLog.objects.create(
            user=request.user,
            date=today,
            start_time=now,
        )
        
        # Update attendance status
        try:
            attendance = Attendance.objects.get(intern=request.user, date=today)
            attendance.is_on_break = True
            attendance.save(update_fields=['is_on_break'])
        except Attendance.DoesNotExist:
            pass
        
        return HttpResponseRedirect(reverse('attendance:break_action'))
    
    elif action == 'end':
        # Can only end break inside office
        lat = form.cleaned_data.get('latitude')
        lon = form.cleaned_data.get('longitude')
        
        settings = _get_office_settings()
        if settings and settings.office_latitude is not None and settings.office_longitude is not None:
            radius = settings.radius_meters or 100
            if lat and lon:
                dist = haversine_meters(lat, lon, settings.office_latitude, settings.office_longitude)
                client_acc = form.cleaned_data.get('accuracy') if 'form' in locals() else None
                if client_acc is not None and client_acc > 2000:
                    return render(request, 'attendance/break_action.html', {'form_errors': 'Location accuracy is too low. Use GPS and retry.'})
                if dist > radius:
                    return render(
                        request,
                        'attendance/break_action.html',
                        {'form_errors': 'You must be inside the office to end your break.'},
                    )
        
        # End break
        active_break = BreakLog.objects.filter(
            user=request.user,
            date=today,
            end_time__isnull=True
        ).first()
        
        if not active_break:
            return render(request, 'attendance/break_action.html', {
                'form_errors': 'You are not on break.'
            })
        
        active_break.end_time = now
        
        # Calculate duration
        duration_seconds = (now - active_break.start_time).total_seconds()
        active_break.duration_minutes = int(duration_seconds // 60)
        active_break.save()
        
        # Update attendance
        try:
            attendance = Attendance.objects.get(intern=request.user, date=today)
            attendance.is_on_break = False
            
            # Recalculate total break time
            breaks = BreakLog.objects.filter(user=request.user, date=today, end_time__isnull=False)
            total_break_minutes = sum(b.duration_minutes for b in breaks)
            attendance.total_break_minutes = total_break_minutes
            
            attendance.save(update_fields=['is_on_break', 'total_break_minutes'])
        except Attendance.DoesNotExist:
            pass
        
        return HttpResponseRedirect(reverse('attendance:break_action'))
    
    return render(request, 'attendance/break_action.html', {
        'form_errors': 'Invalid action.'
    })


@login_required
def admin_office_status(request):
    """Admin view to see all users' current status (in/out of office)."""
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Admins only')

    from django.contrib.auth import get_user_model

    User = get_user_model()

    now = timezone.localtime(timezone.now())
    today = now.date()

    # Bulk-load interns, today attendance, and active breaks to avoid N+1 queries.
    users = list(User.objects.filter(role='intern').order_by('username').only('id', 'username', 'first_name', 'last_name', 'email'))
    user_ids = [u.id for u in users]

    attendance_qs = (
        Attendance.objects.filter(intern_id__in=user_ids, date=today)
        .select_related('intern')
    )
    attendance_by_user_id = {a.intern_id: a for a in attendance_qs}

    active_break_qs = (
        BreakLog.objects.filter(user_id__in=user_ids, date=today, end_time__isnull=True)
        .select_related('user')
    )
    active_break_by_user_id = {b.user_id: b for b in active_break_qs}

    users_data = []
    in_office_count = 0
    on_break_count = 0
    checked_out_count = 0
    not_checked_in_count = 0

    for user in users:
        attendance = attendance_by_user_id.get(user.id)
        active_break = active_break_by_user_id.get(user.id)

        status = 'Not Checked In'
        location = ''

        if attendance and attendance.check_in_time:
            if attendance.check_out_time:
                status = 'Checked Out'
                checked_out_count += 1
            else:
                if attendance.is_on_break:
                    status = 'On Break'
                    on_break_count += 1
                else:
                    status = 'In Office'
                    in_office_count += 1
                location = attendance.check_in_time.strftime('%H:%M')
        else:
            not_checked_in_count += 1

        users_data.append(
            {
                'user': user,
                'attendance': attendance,
                'status': status,
                'location': location,
                'active_break': active_break,
            }
        )

    return render(
        request,
        'attendance/admin_office_status.html',
        {
            'users_data': users_data,
            'in_office_count': in_office_count,
            'on_break_count': on_break_count,
            'checked_out_count': checked_out_count,
            'not_checked_in_count': not_checked_in_count,
        },
    )


@login_required
def admin_user_history(request, user_id=None):
    """Admin view to select a user and see their attendance history."""
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Admins only')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    selected_user = None
    attendances = None
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not user_id:
        user_id = request.GET.get('user_id')

    if user_id:
        try:
            user_id = int(user_id)
            selected_user = User.objects.get(id=user_id, role='intern')
            attendances = Attendance.objects.filter(intern=selected_user).order_by('-date')
            
            if date_from:
                attendances = attendances.filter(date__gte=date_from)
            if date_to:
                attendances = attendances.filter(date__lte=date_to)
        except (User.DoesNotExist, ValueError):
            selected_user = None
            attendances = None
    
    users = User.objects.filter(role='intern').order_by('username')
    
    return render(request, 'attendance/admin_user_history.html', {
        'users': users,
        'selected_user': selected_user,
        'attendances': attendances,
        'date_from': date_from,
        'date_to': date_to,
    })


