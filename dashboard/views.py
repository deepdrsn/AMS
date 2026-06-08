from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render


@login_required
def dashboard_home(request):
    return render(request, 'dashboard/dashboard_home.html')


@login_required
def intern_dashboard(request):
    return render(request, 'dashboard/intern_dashboard.html')


@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        return HttpResponseForbidden('Admins only')
    return render(request, 'dashboard/admin_dashboard.html')

