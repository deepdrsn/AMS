from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from attendance.forms import AttendanceActionForm
from attendance.models import Attendance, DeviceLog
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


def _log_device(request, user, note=''):
    ua = request.META.get('HTTP_USER_AGENT', '')[:500]
    ip = _get_client_ip(request)
    # Lightweight fingerprint: user agent + (ip prefix)
    ua_sig = (ua[:200] + '|' + ip.split('.')[:2].join('.')).encode('utf-8', errors='ignore')
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
        dist = haversine_meters(lat, lon, settings.office_latitude, settings.office_longitude)
        if dist > radius:
            return render(
                request,
                'attendance/check_in.html',
                {'form_errors': 'You are outside the office premises. Attendance denied.'},
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
    late_threshold = timezone.datetime.combine(today, timezone.datetime.min.time()).replace(hour=10, minute=0)
    attendance = Attendance.objects.get(intern=request.user, date=today)
    check_in_dt = timezone.datetime.combine(today, attendance.check_in_time)
    if check_in_dt > late_threshold.replace(tzinfo=timezone.get_current_timezone()):
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
        if dist > radius:
            return render(
                request,
                'attendance/check_out.html',
                {'form_errors': 'You are outside the office premises. Attendance denied.'},
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
    today = now.date()
    attendances = Attendance.objects.filter(intern=request.user).order_by('-date')
    return render(request, 'attendance/history.html', {'attendances': attendances})


@login_required
def export_csv(request):
    if getattr(request.user, 'role', '') != 'admin':
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


