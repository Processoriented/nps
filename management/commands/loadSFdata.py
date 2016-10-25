from django.core.management.base import BaseCommand, CommandError
from nps.models import MapSched



class Command(BaseCommand):
    help = 'Populates data from SalesForce to App'

    def handle(self, *args, **options):
        for sched in MapSched.objects.all():
            if sched.is_due():
                datamap = sched.data_map

                datamap.load_sf_data()
                datamap.save()
                sched.increment_nxt()

                self.stdout.write(
                    'Data refreshed for %s' % datamap.name)
