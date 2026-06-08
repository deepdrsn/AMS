from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminUserForm, CustomAuthenticationForm
from .models import CustomUser


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:intern_dashboard')

    form = CustomAuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('dashboard:intern_dashboard')

    return render(request, 'accounts/login.html', {'form': form})


def _is_admin_user(user):
    return user.is_active and (user.is_superuser or getattr(user, 'role', None) == 'admin')


@login_required
def manage_interns(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Admins only')

    selected_user = None
    user_id = request.GET.get('user_id')
    if user_id:
        selected_user = CustomUser.objects.filter(id=user_id, role=CustomUser.Role.INTERN).first()

    if request.method == 'POST':
        editing_id = request.POST.get('user_id')
        if editing_id:
            selected_user = CustomUser.objects.filter(id=editing_id, role=CustomUser.Role.INTERN).first()
            form = AdminUserForm(request.POST, instance=selected_user)
        else:
            form = AdminUserForm(request.POST)

        if form.is_valid():
            intern = form.save(commit=False)
            intern.role = CustomUser.Role.INTERN
            password = form.cleaned_data.get('password')
            if password:
                intern.set_password(password)
            elif selected_user is None:
                intern.set_unusable_password()
            intern.save()

            action_text = 'updated' if editing_id else 'added'
            messages.success(request, f'Intern {action_text} successfully.')
            return redirect('accounts:manage_interns')
    else:
        form = AdminUserForm(instance=selected_user)

    interns = CustomUser.objects.filter(role=CustomUser.Role.INTERN).order_by('username')
    return render(
        request,
        'accounts/manage_interns.html',
        {
            'form': form,
            'interns': interns,
            'selected_user': selected_user,
        },
    )


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('accounts:login')

