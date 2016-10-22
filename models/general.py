"""Django models for the nps app"""
import os
import requests
from pydoc import locate
from django.db import models
from django.utils import timezone


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

    def __str__(self):
        return self.name

    def prime_obj(self):
        moqs = self.mapobject_set.all()
        prime = None
        for mob in moqs:
            if mob.is_master():
                prime = mob
        return prime

    def apply_model(self, recs, mapobj):
        nrecs = []
        for rec in recs:
            nrec = {}
            for key in rec:
                mqs = mapobj.mapfield_set.filter(
                    sf_api_name=key)
                mtch = None if mqs.count() == 0 else mqs[0].dj_attr
                val = rec[key]
                if mtch:
                    nrec[mtch] = val
            nrecs.append(nrec)
        return nrecs

    def needs_deps(self, recs, mapobj):
        rtn = {}
        rflds = {
            x.dj_attr: x
            for x in mapobj.mapfield_set.filter(
                sf_relation__isnull=False)}
        for rec in recs:
            for key in rec:
                if key in rflds.keys():
                    dcn = rflds[key].sf_relation__dj_class
                    dlocn = 'nps.models.nps.'
                    dlocn = dlocn + dcn
                    dklass = locate(dlocn)
                    qst = dklass.objects.filter(sfid=rec[key])
                    if qst.count() == 0:
                        if rtn[dcn]:
                            if not(rec[key] in rtn[dcn]):
                                rtn[dcn]['ids'].append(rec[key])
                        else:
                            rtn[dcn] = {
                                'mobj': rflds[key],
                                'ids': [rec[key]]}
        return rtn

    def load_object(self, mapobj, rtfilt=None):
        qs = mapobj.apiqs(rtfilt)
        sfd = self.api_cred.get_data(qs)
        inprog = True
        while inprog:
            recs = self.apply_model(sfd['records'], mapobj)
            needed = self.needs_deps(recs, mapobj)
            while needed:
                for dep in needed:
                    rtf = "Id+in+('" 
                    rtf = rtf + "','".join(dep['ids'][:249])
                    rtf = rtf + "')"
                    self.load_object(dep['mobj'], rtf)
                needed = self.needs_deps(recs, mapobj)
            locn = 'nps.models.nps.' + mapobj.dj_class
            klass = locate(locn)
            for rec in recs:
                ckc = klass.objects.filter(sfid=rec['sfid'])
                if ckc.count() > 0:
                    if ckc[0].systemmodstamp < rec['systemmodstamp']:
                        ckc[0].update(**rec)
                else:
                    nr = klass.objects.create(**rec)
                    nr.save()
            if sfd['finished']:
                inprog = False
            else:
                sfd = self.api_cred.get_data(sfd['next'])        

    def load_sf_data(self):
        prime = self.prime_obj()
        self.load_object(prime)


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

    def get_field_by_dj_attr(self, filtr):
        qs = self.mapfield_set.filter(dj_attr=filtr)


    def cr_trgt_inst(self, **kwargs):
        for field in kwargs:


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

    def has_rels(self):
        """check if any child objects"""
        rqs = self.mapfield_set.filter(sf_relation__isnull=False)
        return rqs.count() > 0

    def apirqs(self):
        """get related field api queries"""
        rfqs = self.mapfield_set.filter(sf_relation__isnull=False)
        cowc = self.apiqsw()
        odefs = []
        for relf in rfqs:
            relo = relf.sf_relation
            sqlist = [
                'Id', 'in', '(SELECT',
                relf.sf_api_name, 'FROM',
                self.sf_api_name]
            if cowc:
                sqlist.append('WHERE')
                sqlist.append(cowc)
            sqtxt = "+".join(sqlist) + ')'
            odef = {
                'mapobj': relo,
                'relqs': relo.apiqs(sqtxt)}
            odefs.append(odef)
        return odefs

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
            curdt = timezone.now()
            tmd = timezone.timedelta(days=self.logic_param)
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
        default=timezone.now)

    class Meta:
        abstract = True

    def __str__(self):
        return self.sfid

    def url(self):
        """gets url for record in SF"""
        sflink = 'https://gehealthcare-svc.my.salesforce.com/'
        return sflink + self.sfid
