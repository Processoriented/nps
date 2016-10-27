from django.utils import timezone as dtz
from django.core.management.base import BaseCommand, CommandError
from nps.models import MapSched



class Command(BaseCommand):
    help = 'Populates data from SalesForce to App'

    def handle(self, *args, **options):
        self.report('Checking schedules')
        for sched in MapSched.objects.all():
            datamap = sched.data_map
            if sched.is_due():
                self.report('Updating %s' % str(sched))
                datamap.load_sf_data()
                datamap.save()
                sched.increment_nxt()

                self.report(
                    'Data refreshed for %s' % datamap.name)
            else:
                self.report('%s not yet due.' % str(sched))

    def report(self, msg):
        dts = dtz.now().isoformat()
        self.stdout.write('%s: %s' % (dts, msg))
