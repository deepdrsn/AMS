# Hajiri (Attendance Management)

A Django-based internal attendance management system 

## Features
- Admin/Intern roles with secure authentication
- Intern check-in/check-out with:
  - Browser geolocation radius validation (office premises)
  - Duplicate check prevention
  - Late detection and total working hours
- office Wi-Fi / IP-range validation (via configured CIDRs)
- Device/browser logging
- Admin dashboard with filters, search, and CSV export

## Tech Stack
- Backend: Django (Python)
- Frontend: Django Templates + Bootstrap 5
- Database: SQLite 

## Notes
- Geolocation requires browser permission.
- Wi-Fi validation uses client IP vs configured CIDR ranges (best-effort).

