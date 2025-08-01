import pandas as pd
from datetime import datetime, timedelta
import re

# Required columns for timesheet CSV
REQUIRED_COLUMNS = ['worker_id', 'date', 'time_in', 'time_out', 'agency', 'position']
OPTIONAL_COLUMNS = ['lunch_minutes']

# Valid position values
VALID_POSITIONS = ['general labor', 'forklift driver']

# Time format regex patterns
TIME_PATTERN = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
# Accept both YYYY-MM-DD and M/D/YY formats
DATE_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2})$')

def validate_csv_columns(df):
    """Validate that the CSV contains all required columns."""
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    return True

def validate_time_format(time_str):
    """Validate time string format (HH:MM)."""
    if not TIME_PATTERN.match(time_str):
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")
    return True

def parse_date(date_str):
    """Parse date string in either YYYY-MM-DD or M/D/YY format."""
    try:
        # Try YYYY-MM-DD format first
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            # Try M/D/YY format
            return datetime.strptime(date_str, '%m/%d/%y')
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or M/D/YY")

def validate_date_format(date_str):
    """Validate date string format (YYYY-MM-DD or M/D/YY)."""
    if not DATE_PATTERN.match(date_str):
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or M/D/YY")
    try:
        parse_date(date_str)
    except ValueError as e:
        raise ValueError(str(e))
    return True

def validate_lunch_minutes(lunch_str):
    """Validate lunch minutes value."""
    if not lunch_str:
        return 30  # Default value
    try:
        minutes = int(lunch_str)
        if minutes < 0 or minutes > 120:
            raise ValueError("Lunch minutes must be between 0 and 120")
        return minutes
    except ValueError:
        raise ValueError(f"Invalid lunch minutes: {lunch_str}")

def validate_worker_id(worker_id):
    """Validate worker ID format."""
    if not worker_id or not isinstance(worker_id, str):
        raise ValueError("Worker ID must be a non-empty string")
    if not worker_id.strip():
        raise ValueError("Worker ID cannot be empty or whitespace")
    return True

def validate_agency(agency):
    """Validate agency name."""
    if not agency or not isinstance(agency, str):
        raise ValueError("Agency must be a non-empty string")
    if not agency.strip():
        raise ValueError("Agency cannot be empty or whitespace")
    return True

def validate_position(position):
    """Validate worker position."""
    if not position or not isinstance(position, str):
        raise ValueError("Position must be a non-empty string")
    position_lower = position.strip().lower()
    if position_lower not in VALID_POSITIONS:
        raise ValueError(f"Position must be one of: {', '.join(VALID_POSITIONS)}. Got: {position}")
    return True

def normalize_position(position):
    """Normalize position to standard format."""
    if not position:
        return None
    return position.strip().lower()

def get_base_rate_for_position(position):
    """Get the base hourly rate for a given position."""
    normalized_position = normalize_position(position)
    if normalized_position == 'general labor':
        return 16.0
    elif normalized_position == 'forklift driver':
        return 18.0
    else:
        raise ValueError(f"Unknown position: {position}")

def get_markup_for_agency(agency):
    """Get the markup percentage for a given agency."""
    if agency in ('JJ', 'JJ Staffing'):
        return 0.25
    elif agency in ('Stride', 'Stride Staffing'):
        return 0.30
    else:
        return 0.0

def calculate_shift_duration(time_in, time_out):
    """Calculate the duration of a shift, handling overnight cases."""
    # Convert times to datetime objects for the same date
    base_date = datetime(2000, 1, 1)  # Arbitrary date, we only care about time
    dt_in = datetime.combine(base_date, time_in)
    dt_out = datetime.combine(base_date, time_out)
    
    # If time_out is earlier than time_in, it's an overnight shift
    if dt_out <= dt_in:
        dt_out += timedelta(days=1)
    
    duration = (dt_out - dt_in).total_seconds() / 3600.0
    return duration

def validate_timesheet_row(row):
    """Validate a single timesheet row."""
    required_fields = ['worker_id', 'date', 'time_in', 'time_out', 'agency', 'position']
    for field in required_fields:
        if field not in row or pd.isnull(row[field]) or row[field] is None or str(row[field]).strip() == '':
            raise ValueError(f"Missing value for required field '{field}'")
    try:
        validate_worker_id(row['worker_id'])
        validate_date_format(row['date'])
        validate_time_format(row['time_in'])
        validate_time_format(row['time_out'])
        validate_agency(row['agency'])
        validate_position(row['position'])
        if 'lunch_minutes' in row:
            validate_lunch_minutes(row['lunch_minutes'])
        # Validate time logic
        time_in = datetime.strptime(row['time_in'], '%H:%M').time()
        time_out = datetime.strptime(row['time_out'], '%H:%M').time()
        # Calculate shift duration
        duration = calculate_shift_duration(time_in, time_out)
        # Validate shift duration is reasonable (e.g., not more than 24 hours)
        if duration > 24:
            raise ValueError(f"Shift duration of {duration:.1f} hours is too long")
        if duration < 0.5:
            raise ValueError(f"Shift duration of {duration:.1f} hours is too short")
        return True
    except KeyError as e:
        raise ValueError(f"Missing required field: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Invalid data: {str(e)}")

def validate_timesheet_data(df):
    """Validate the entire timesheet DataFrame."""
    validate_csv_columns(df)
    # Convert dates to consistent format
    df['date'] = df['date'].apply(lambda x: parse_date(x).strftime('%Y-%m-%d') if pd.notnull(x) and x != '' else x)
    errors = []
    for idx, row in df.iterrows():
        try:
            validate_timesheet_row(row)
        except ValueError as e:
            errors.append(f"Row {idx + 2}: {str(e)}")  # +2 for header and 0-index
    if errors:
        raise ValueError("\n".join(errors))
    return True 