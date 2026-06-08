!i## Admin-facing user status/history UI improvements

### Step 1
- Inspect existing admin views/templates for user status/history.

### Step 2 (Implemented)
- Fix N+1 query performance in `admin_office_status` by bulk-loading `Attendance` and active `BreakLog` records.

### Step 3 (Implemented)
- Fix `admin_user_history.html` status rendering so it no longer depends on `attendance.status` string values; use `check_in_time/check_out_time` + `is_on_break`.

### Step 4 (Not implemented)
- Improve admin history UI ergonomics: searchable user list (client-side), clear date filters, sticky table header.


### Step 5 (Implemented)
- Improve `admin_office_status.html` counters so “Checked Out” and “Not Checked In” reflect real data.

### Step 6
- Run the Django app / sanity-check pages:
  - `/attendance/admin/office-status/`
  - `/attendance/admin/user-history/`
  - user detail view with date filters


