from django.core.management.base import BaseCommand
from fiscalisation.services import FiscalisationService


class Command(BaseCommand):
    help = 'Resume fiscalisation'
    
    def handle(self, *args, **options):
        service = FiscalisationService()
        service.resume_fiscalisation()
        self.stdout.write(self.style.SUCCESS('Fiscalisation resumed'))