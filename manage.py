#!/usr/bin/env python
"""Django's command-line utility."""
import os
import sys

def main():
    # Default to development settings (SQLite) on your dev machine
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'point_of_sale.settings_dev')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()