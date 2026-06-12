from django.core.management.base import BaseCommand
from fiscalisation.services import FiscalisationService


class Command(BaseCommand):
    help = 'Sync pending fiscal receipts to Binary API'
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Maximum receipts to sync')
    
    def handle(self, *args, **options):
        service = FiscalisationService()
        results = service.sync_pending_receipts(limit=options['limit'])
        self.stdout.write(self.style.SUCCESS(
            f"Sync complete: {results['success']} synced, {results['failed']} failed out of {results['total']}"
        ))