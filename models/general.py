"""Django models for the nps app"""
import os
import requests
import datetime
from pydoc import locate
from django.db import models
from django.utils import timezone as dtz


def proxies():
    """Gets proxys from environmental variables if they exist"""
    proxd = {}
    try:
        proxd['http'] = os.environ['HTTP_PROXY']
        proxd['https'] = os.environ['HTTPS_PROXY']
    except KeyError:
        proxd = None
    return proxd


class ForceAPI(models.Model):
    """Credentials and methods for Salesforce REST API connection"""
    user_id = models.EmailField(max_length=80)
    password = models.CharField(max_length=80)
    user_token = models.CharField(max_length=80)
    consumer_key = models.CharField(max_length=120)
    consumer_secret = models.CharField(max_length=120)
    request_token_url = models.CharField(
        max_length=255,
        default='https://login.salesforce.com/services/oauth2/token')
    access_token_url = models.CharField(
        max_length=255,
        default='https://login.salesforce.com/services/oauth2/token')
    conn = None

    def __str__(self):
        return self.user_id

    def create_connection(self):
        """Creates API Connection"""
        data = {
            'grant_type': 'password',
            'client_id': self.consumer_key,
            'client_secret': self.consumer_secret,
            'username': self.user_id,
            'password': self.password
        }
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        if proxies():
            req = requests.post(
                self.access_token_url,
                data=data,
                headers=headers,
                proxies=proxies())
        else:
            req = requests.post(
                self.access_token_url,
                data=data,
                headers=headers)

        self.conn = req.json()
        return req.json()

    def test_connection(self):
        """tests if connection is still working"""
        if self.conn:
            tsthdr = {
                'Authorization': 'Bearer ' + self.conn['access_token']
            }
            tsturl = self.conn['instance_url']
            tsturl = tsturl + '/services/data/v37.0/sobjects'
            tst = requests.get(tsturl, headers=tsthdr, proxies=proxies())
            return tst.status_code == 200

        return False

    def get_connection(self):
        """gets a live connection to the REST API"""
        if not self.test_connection():
            return self.create_connection()
        else:
            return self.conn

    def get_data(self, apifunction):
        """gets data defined in the apifunction"""
        cnn = self.get_connection()
        hdr = {
            'Authorization': 'Bearer ' + cnn['access_token']
        }
        url = cnn['instance_url'] + '/services/data/v37.0/' + apifunction
        grs = requests.get(url, headers=hdr, proxies=proxies())
        return grs.json()


class DataMap(models.Model):
    """Mapping information between SF, Django NPS app, and MySql"""
    name = models.CharField(max_length=80)
    api_cred = models.ForeignKey(
        ForceAPI,
        on_delete=models.CASCADE)
    map_active = models.BooleanField(default=False)
    last_refresh = models.DateTimeField(
        null=True,
        blank=True)

    def __str__(self):
        return self.name

    def nxt_refresh(self):
        rtn = None
        for sched in self.mapsched_set.all():
            ed = sched.next_itr if sched.end is None else sched.end
            if not(sched.next_itr > ed):
                snxt = sched.next_itr
                if rtn is None:
                    rtn = snxt
                else:
                    rtn = rtn if snxt < rtn else snxt
        return rtn

    def sf_recs(self, qs):
        rtn = None
        req = self.api_cred.get_data(qs)
        if 'records' in req.keys():
            rtn = req['records']
            if not(req['done']):
                nqs = req['nextRecordsUrl'][21:]
                rtn.append(self.sf_recs(nqs))
        return rtn

    def prime_obj(self):
        moqs = self.mapobject_set.all()
        prime = None
        for mob in moqs:
            if mob.is_master():
                prime = mob
        return prime   

    def load_sf_data(self):
        prime = self.prime_obj()
        prime.load_obj()
        self.update_refresh()

    def update_refresh(self):
        now = dtz.now()
        then = now + datetime.timedelta(days=-999)
        nd = now + datetime.timedelta(days=-999)
        moqs = self.mapobject_set.all()
        for mo in moqs:
            if mo.last_refresh:
                if mo.last_refresh > nd:
                    nd = mo.last_refresh
        if nd > then:
            self.last_refresh = nd
            self.save()


class MapSched(models.Model):
    UNIT_OPTS = (
        ('HR', 'Hours'),
        ('DY', 'Days'),
        ('WK', 'Weeks'),
        ('MO', 'Months'),
        ('YR', 'Years'),)
    data_map = models.ForeignKey(
        DataMap,
        on_delete=models.CASCADE)
    frequency = models.IntegerField()
    freq_unit = models.CharField(
        max_length=2,
        choices=UNIT_OPTS)
    start = models.DateTimeField(
        default=dtz.now)
    end = models.DateTimeField(
        null=True,
        blank=True)
    next_itr = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        default=dtz.now)

    def __str__(self):
        unt = [d for d in self.UNIT_OPTS if d[0] == self.freq_unit]
        unt = unt[0][1]
        unt = unt[:-1] if self.frequency == 1 else unt
        return '%s: every %s %s starting %s' % (
            self.data_map.name,
            str(self.frequency),
            unt,
            self.next_itr.isoformat())

    def incr_opt(self, idt):
        if self.freq_unit == 'HR':
            hrs = self.frequency
            return idt + datetime.timedelta(hours=hrs)
        elif self.freq_unit == 'DY':
            daze = self.frequency
            return idt + datetime.timedelta(days=daze)
        elif self.freq_unit == 'WK':
            wks = self.frequency
            return idt + datetime.timedelta(days=wks)
        elif self.freq_unit == 'MO':
            premonth = idt.month
            nxtyear = idt.year
            nxtmonth = premonth + self.frequency
            while nxtmonth > 12:
                nxtyear = nxtyear + 1
                nxtmonth = nxtmonth - 12
            return idt.replace(year=nxtyear, month=nxtmonth)
        elif self.freq_unit == 'YR':
            yr = idt.year + self.frequency
            return idt.replace(year=yr)

    def is_due(self):
        if not(self.end is None):
            if self.end < dtz.now():
                return False
        if self.start > dtz.now():
            return False
        if not(self.data_map.map_active):
            return False
        if self.next_itr is None:
            self.next_itr = self.start
            self.save()
        if self.start > self.next_itr:
            self.next_itr = self.start
            self.save()
        lstDone = self.data_map.last_refresh
        if lstDone is None:
            return True
        exptd = self.incr_opt(lstDone)
        if exptd > self.next_itr:
            exptd = self.next_itr
        return exptd < dtz.now()

    def increment_nxt(self):
        if self.next_itr is None:
            self.next_itr = self.start
            self.save()
        while self.next_itr < dtz.now():
            self.next_itr = self.incr_opt(self.next_itr)
            self.save()


class MapObject(models.Model):
    """Provides Objects for the DataMap"""
    data_map = models.ForeignKey(
        DataMap,
        on_delete=models.CASCADE)
    sf_api_name = models.CharField(max_length=80)
    sf_label = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    dj_class = models.CharField(
        max_length=40,
        null=True,
        blank=True)
    db_table = models.CharField(
        max_length=64,
        null=True,
        blank=True)
    last_refresh = models.DateTimeField(
        null=True,
        blank=True)
    record_count = models.IntegerField(
        null=True,
        blank=True,
        default=0)

    def get_field(self, sf_api_name):
        qs = self.mapfield_set.filter(sf_api_name=sf_api_name)
        if qs.count() == 0:
            return None
        else:
            return qs[0]

    def get_mapped(self):
        locn = 'nps.models.' + self.dj_class
        return locate(locn)

    def get_one(self, sfid):
        rtfilt = "Id='" + sfid + "'"
        return self.get_sf_recs(rtfilt)

    def get_sf_recs(self, rtfilt=None):
        qs = self.apiqs(rtfilt)
        resp = self.data_map.sf_recs(qs)
        return resp

    def apply_map(self, rec):
        rtn = {}
        for key in rec:
            mf = self.get_field(key)
            if mf:
                rtn[mf.dj_attr] = rec[key]
        return rtn

    def fkfields(self):
        """check if any child objects"""
        rtn = {}
        rqs = self.mapfield_set.filter(sf_relation__isnull=False)
        for mf in rqs:
            rtn[mf.dj_attr] = mf
        return rtn

    def check_deps(self, rec):
        rtn = {'rec': {}, 'ndd': {}}
        for key, val in rec.items():
            fks = self.fkfields()
            if key in fks.keys() and not(val is None):
                relobj = fks[key].sf_relation.get_mapped()
                luqs = relobj.objects.filter(sfid=val)
                if luqs.count() == 0:
                    djc = fks[key].sf_relation.dj_class
                    rtn['ndd'][djc] = val
                else:
                    rtn['rec'][key] = luqs[0]
            else:
                rtn['rec'][key] = val
        return rtn

    def is_newer(self, frec, rqs):
        try:
            nd = frec['systemmodstamp']
            cqs = rqs.filter(systemmodstamp__lt=nd)
            return cqs.count() > 0
        except:
            return False

    def load_recs(self, recs, ct=0):
        if ct > 900:
            return
        need_deps = {}
        deferred = []
        klass = self.get_mapped()
        for rec in recs:
            frec = self.apply_map(rec)
            deps = self.check_deps(frec)
            if deps['ndd']:
                for key, val in deps['ndd'].items():
                    if not(key in need_deps.keys()):
                        need_deps[key] = []
                    if not(val in need_deps[key]):
                        need_deps[key].append(val)
                    deferred.append(rec)
            elif 'sfid' in deps['rec'].keys():
                rqs = klass.objects.filter(sfid=deps['rec']['sfid'])
                if rqs.count() == 0:
                    nr = klass.objects.create(**deps['rec'])
                    nr.save()
                elif self.is_newer(deps['rec'], rqs):
                    rqs.update(**deps['rec'])
        for key, val in need_deps.items():
            ids = val[:249]
            rtfilt = "Id+in+('" + "','".join(ids) + "')"
            relqs = self.data_map.mapobject_set.filter(dj_class=key)
            relmo = relqs[0]
            drecs = relmo.get_sf_recs(rtfilt)
            relmo.load_recs(drecs)
        if len(deferred) > 0:
            self.load_recs(deferred, ct+1)
        self.set_stats()

    def set_stats(self):
        self.set_refreshed()
        self.set_rec_ct()

    def set_rec_ct(self):
        mo = self.get_mapped()
        ct = mo.objects.all().count()
        cur = self.record_count or 0
        if cur < ct:
            self.record_count = ct
            self.save()

    def set_refreshed(self):
        now = dtz.now()
        then = now + datetime.timedelta(days=-1)
        cur = self.last_refresh or then
        if cur < now:
            self.last_refresh = now
            self.save()

    def load_obj(self):
        recs = self.get_sf_recs()
        self.load_recs(recs)

    def apiqsw(self, rtfilt=None):
        """Returns Where Clause of query"""
        fqs = self.mapfield_set.all()
        fltrs = []
        for fld in fqs:
            fltrs.extend([flt.fltr_txt() for flt in fld.mapfilter_set.all()])
        if rtfilt:
            fltrs.append(rtfilt)
        if (len(fltrs) > 0):
            return "+AND+".join(fltrs)
        else:
            return None

    def apiqs(self, rtfilt=None):
        """Returns Query for api"""
        fqs = self.mapfield_set.all()
        selflds = [fld.sf_api_name for fld in fqs]
        qlist = [
            'query?q=SELECT',
            ','.join(selflds),
            'FROM',
            self.sf_api_name]
        whc = self.apiqsw(rtfilt)
        if whc:
            qlist.append('WHERE')
            qlist.append(whc)
        return "+".join(qlist)

    def is_master(self):
        """check if has a parent object"""
        rqs = MapField.objects.filter(sf_relation__pk=self.pk)
        return rqs.count() == 0

    def __str__(self):
        return self.dj_class


class MapField(models.Model):
    """Provides Fields for the DataMap"""
    map_object = models.ForeignKey(
        MapObject,
        on_delete=models.CASCADE)
    sf_api_name = models.CharField(max_length=80)
    sf_label = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    sf_relation = models.ForeignKey(
        MapObject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sf_relation')
    dj_attr = models.CharField(
        max_length=40,
        null=True,
        blank=True)
    db_field = models.CharField(
        max_length=64,
        null=True,
        blank=True)

    def __str__(self):
        spl = [
            self.map_object.dj_class,
            self.dj_attr]
        return '.'.join(spl)


class MapFilter(models.Model):
    """Filter Definition for the DataMap"""
    OPERATORS = (
        ('=', 'Equals'), ('!=', 'Not equal'),
        ('<', 'Less Than'), ('<=', 'Less than or equal'),
        ('>=', 'Greater than or equal'),
        ('>', 'Greater than'),
        ('StartsWith', 'Starts With'),
        ('Contains', 'Contains'),
        ('EndsWith', 'Ends With'),
        ('in', 'in'), ('not in', 'not in'),
        ('includes', 'includes'),
        ('excludes', 'excludes'),)
    LOGICALS = (
        ('DELTAxDAYS', 'Offset x Days from now'),
        ('FLDCMPR', 'Compare to x Field'),)
    map_field = models.ForeignKey(
        MapField,
        on_delete=models.CASCADE)
    operator = models.CharField(
        max_length=20,
        choices=OPERATORS)
    value = models.CharField(
        max_length=150,
        null=True,
        blank=True)
    logic = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        choices=LOGICALS)
    logic_param = models.IntegerField(
        null=True,
        blank=True)

    def delta_days_logic(self):
        """Creates delta_days logical filter at runtime"""
        valid = (MapFilter.objects.filter(
            logic='DELTAxDAYS',
            logic_param__isnull=False,
            pk=self.pk).count() == 1)
        rtn = None
        if valid:
            curdt = dtz.now()
            tmd = datetime.timedelta(days=self.logic_param)
            fdt = curdt + tmd
            sdt = fdt.isoformat().split('+')[0][0:-3] + 'Z'
            rtn = self.map_field.sf_api_name
            rtn = rtn + self.operator + sdt
        return rtn

    def fld_comp_logic(self):
        """Creates field comparison logical filter"""
        valid = (MapFilter.objects.filter(
            logic='FLDCMPR',
            logic_param__isnull=False,
            pk=self.pk).count() == 1)
        rtn = None
        if valid:
            cfld = MapField.objects.get(pk=self.logic_param)
            rtn = self.map_field.sf_api_name
            rtn = rtn + self.operator
            rtn = rtn + cfld.sf_api_name
        return rtn

    def fltr_txt(self):
        """generates filter text for API call"""
        rtn = self.delta_days_logic()
        if not(rtn):
            rtn = self.fld_comp_logic()
            if not(rtn):
                rtn = self.map_field.sf_api_name
                rtn = rtn + self.operator
                rtn = rtn + self.value
        return rtn

    def __str__(self):
        return self.fltr_txt()


class CommonInfo(models.Model):
    """Common Fields for all SF based classes"""
    sfid = models.CharField(
        max_length=18,
        primary_key=True,
        db_column='id')
    name = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    systemmodstamp = models.DateTimeField(
        default=dtz.now)
    map_object = models.ForeignKey(
        MapObject,
        null=True,
        on_delete=models.SET_NULL)

    class Meta:
        abstract = True

    def __str__(self):
        return self.sfid

    def url(self):
        """gets url for record in SF"""
        sflink = 'https://gehealthcare-svc.my.salesforce.com/'
        return sflink + self.sfid
