from django.core.management.base import BaseCommand
from fiscalisation.services import FiscalisationService


class Command(BaseCommand):
    help = 'Pause fiscalisation'
    
    def add_arguments(self, parser):
        parser.add_argument('--reason', type=str, help='Reason for pausing')
    
    def handle(self, *args, **options):
        service = FiscalisationService()
        service.pause_fiscalisation(reason=options.get('reason', ''), user='cli')
        self.stdout.write(self.style.WARNING('Fiscalisation paused'))