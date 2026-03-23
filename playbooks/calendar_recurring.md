# Playbook: Android Calendar Recurring Events

## Problem
`content query --uri content://com.android.calendar/events` returns only original event templates, not computed recurring instances (birthdays, weekly meetings).

## Expert Solution
If you need to find events in a date range:
1. Query all events with `rrule IS NOT NULL`.
2. Get `dtstart` and `rrule` fields.
3. Use `termux_shell` to run a Python script with `dateutil.rrule` or manual logic to expand instances.
4. Compare expanded timestamps with your target range.

## Example Python logic for expansion:
```python
# In termux_shell:
# 1. content query -> get data
# 2. python script to expand:
for year in range(current_year - 1, current_year + 2):
    instance = original_date.replace(year=year)
    if start_range <= instance <= end_range:
        print(f"Found: {title} at {instance}")
```
