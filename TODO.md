# Hajiri Attendance System - Implementation Checklist

## Step 1: Scaffolding
- [x] Create Django project structure (hajiri/ package) and apps: accounts/, attendance/, dashboard/, core/
- [x] Configure settings for templates/bootstrap base template directory + app URLs
- [ ] Configure SQLite + login redirects (remaining)


## Step 2: Core Models
- [ ] Implement OfficeSettings model (lat/lon, radius_meters, optional wifi CIDRs)
- [ ] Implement DeviceLog model

## Step 3: Authentication / Roles
- [ ] Implement accounts app: custom User model or profile-based roles (Admin/Intern)
- [ ] Implement secure login/logout
- [ ] Restrict access by role

## Step 4: Attendance Logic
- [ ] Implement Attendance model
- [ ] Implement check-in/out views with:
  - [ ] Browser geolocation capture + server-side haversine radius validation
  - [ ] Prevent duplicate check-ins
  - [ ] Prevent check-out without check-in
  - [ ] Late detection
  - [ ] Total working hours computation

## Step 5: Device Tracking
- [ ] Create DeviceLog entries on attendance actions and login
- [ ] Admin views to inspect device logs

## Step 6: Admin Dashboard
- [ ] Admin dashboard templates (late arrivals, absentees, total hours)
- [ ] Filters (date, intern, status) + search

## Step 7: Reports & Export
- [ ] CSV export endpoint for attendance records
- [ ] Monthly attendance summary + basic analytics cards

## Step 8: UI/UX
- [ ] Bootstrap 5 templates: base layout, sidebar, intern dashboard, tables

## Step 9: Django Admin Configuration
- [ ] Register models and configure admin filters/search

## Step 10: Migrations & Run Instructions
- [ ] Create migrations
- [ ] Provide setup instructions in README.md
- [ ] Verify end-to-end workflow

