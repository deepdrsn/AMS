from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('intern/', views.intern_dashboard, name='intern_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
]

