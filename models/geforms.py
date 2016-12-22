from django.db import models
from django.utils import timezone
from .general import proxies
from .nps import ServiceOrder
import requests


class Forms_Access(models.Model):
    name = models.CharField(max_length=80)
    client_id = models.CharField(max_length=160)
    client_secret = models.CharField(max_length=80)

    scope = 'GECorp_Forms_API'
    access_token_url = 'https://fssfed.ge.com/fss/as/token.oauth2'
    access_token_expires = None
    access_token = None

    def __str__(self):
        return self.name

    def _access_token_params(self):
        return {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }

    def get_access_token(self, params=None):
        data = params if params is not None else self._access_token_params()
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        req = self.post(
            self.access_token_url,
            data,
            headers)
        if req.status_code == 200:
            rj = req.json()
            secs = 7199
            if 'expires_in' in rj:
                secs = rj['expires_in']
            if 'access_token' in rj:
                self.access_token = rj['access_token']
                self.access_token_expires = timezone.now()
                self.access_token_expires += timezone.timedelta(seconds=secs)
                return self.access_token
            else:
                return rj
        else:
            return req

    def post(self, url, data, headers=None):
        if headers is None:
            headers = self.api_call_headers()
        if proxies():
            return requests.post(
                url,
                headers=headers,
                data=data,
                proxies=proxies())
        else:
            return requests.post(
                url,
                headers=headers,
                data=data)

    def get(self, url, headers=None):
        if headers is None:
            headers = self.api_call_headers()
        if proxies():
            return requests.post(
                url,
                headers=headers,
                proxies=proxies())
        else:
            return requests.post(
                url,
                headers=headers)


    def api_call_headers(self):
        return {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + self.check_access_token()
        }

    def check_access_token(self):
        if self.access_token_expires is None:
            self.access_token = None
        elif timezone.now() > self.access_token_expires:
            self.access_token = None
            self.access_token_expires = None
        if self.access_token is None:
            self.get_access_token()
        return self.access_token

    def get_available_forms(self):
        url = 'https://api.ge.com/gecorp/forms/v1/forms'
        return self.get(url, self.api_call_headers())


class Survey_Form(models.Model):
    name = models.CharField(max_length=80)
    form_id = models.IntegerField()
    access = models.ForeignKey(
        Forms_Access,
        on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Form_Fields(models.Model):
    pass


class Survey_Record(models.Model):
    work_order = models.ForeignKey(
        ServiceOrder,
        null=True,
        on_delete=models.SET_NULL)
    forms_id = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    survey_form = models.ForeignKey(
        Survey_Form,
        on_delete=models.CASCADE)
    wo_name = models.CharField(max_length=80)
    last_update = models.DateTimeField(null=True)
    nps = models.IntegerField(null=True)
    nss_eodb = models.IntegerField(null=True)
    nss_cc = models.IntegerField(null=True)
    nss_fe = models.IntegerField(null=True)
    nss_ftf = models.IntegerField(null=True)
    nss_ttr = models.IntegerField(null=True)
    gc_compare = models.IntegerField(null=True)
    request_contact = models.BooleanField(default=False)
    cust_comments = models.TextField(null=True)
    survey_link = models.CharField(
        null=True,
        max_length=255)

    def __str__(self):
        return self.wo_name

    def find_filt(self):
        return {
            "field_id": 1588082,
            "operator": "eq",
            "value": self.wo_name
        }

    def find_record(self):
        access = self.survey_form.access
        body = {
            'offset': 0,
            'limit': 499,
            'fields': [
                "record_id",
                "dt_updated",
                1588082, # wo_name
                1672513, # nss_eodb
                1672514, # nss_cc
                1672515, # nss_fe
                1672516, # nss_ftf
                1672517, # nss_ttr
                1672518, # gc_compare
                1672519, # request_contact
                1672526, # cust_comments
                1631523 # survey_link
            ],
            'filters': {
                'and': self.find_filt()
            },
            'sort': {},
            'case_sensitive': True
        }
        request_url = "https://api.ge.com/gecorp/forms/v1/forms/"
        request_url += "%s/records" % self.survey_form.form_id
        return access.post(request_url, body)
