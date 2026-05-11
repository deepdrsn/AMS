# Hajiri (Intern Attendance Management)

A Django-based internal attendance management system for telecom interns.

## Features
- Admin/Intern roles with secure authentication
- Intern check-in/check-out with:
  - Browser geolocation radius validation (office premises)
  - Duplicate check prevention
  - Late detection and total working hours
- Optional office Wi-Fi / IP-range validation (via configured CIDRs)
- Device/browser logging
- Admin dashboard with filters, search, and CSV export

## Tech Stack
- Backend: Django (Python)
- Frontend: Django Templates + Bootstrap 5
- Database: SQLite (default) / upgradeable to PostgreSQL

## Setup (local)
1. Open a terminal in this folder: `c:/Users/user/ntc/hajiri`
2. Create and activate a virtual environment:
   - Windows (PowerShell):
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
5. Create an admin user:
   - `python manage.py createsuperuser`
6. (Optional) Seed office settings in admin:
   - Create one `OfficeSettings` row
7. Start server:
   - `python manage.py runserver`

## Notes
- Geolocation requires browser permission.
- Wi-Fi validation uses client IP vs configured CIDR ranges (best-effort).

