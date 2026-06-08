from django.urls import path

from . import views

app_name = 'attendance'

urlpatterns = [
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out, name='check_out'),
    path('history/', views.history, name='history'),
    path('export/', views.export_csv, name='export_csv'),
    path('break/', views.break_action, name='break_action'),
    path('admin/office-status/', views.admin_office_status, name='admin_office_status'),
    path('admin/user-history/', views.admin_user_history, name='admin_user_history'),
    path('admin/user-history/<int:user_id>/', views.admin_user_history, name='admin_user_history_detail'),
]

