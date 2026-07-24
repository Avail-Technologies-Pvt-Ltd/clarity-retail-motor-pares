import os
from datetime import datetime
from django.conf import settings

def log_activity(content, user):
    now = datetime.now()
    date_str = now.strftime("%d/%b/%Y %H:%M:%S")
    
    # Generate filename: month_year.txt (e.g., Jul_2026.txt)
    filename = now.strftime("%b_%Y") + ".txt"
    file_path = os.path.join(settings.BASE_DIR, 'logs', filename)
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Format the log entry with timestamp and user
    log_entry = f"[{date_str}] {user}: {content}"
    
    # Append or create the file
    with open(file_path, 'a+', encoding='utf-8') as file:
        file.write(log_entry + '\n')
    
    return log_entry