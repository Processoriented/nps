from django.db import models
from django.utils import timezone
from .general import CommonInfo



class Case(CommonInfo):
    """Copy of SF Case Object"""
    createddate = models.DateTimeField(
        null=True,
        blank=True)

    class Meta:
        """Django Meta options"""
        db_table = 'case'


class Account(CommonInfo):
    """Copy of SF Account Object"""
    global_region_c = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    global_subregion_c = models.CharField(
        max_length=80,
        null=True,
        blank=True)

    class Meta:
        """Django Meta options"""
        db_table = 'account'


class Contact(CommonInfo):
    """Copy of SF Contact Object"""
    phone = models.CharField(
        max_length=40,
        null=True,
        blank=True)
    email = models.EmailField(
        max_length=80,
        null=True,
        blank=True)

    class Meta:
        """Django Meta Options"""
        db_table = 'contact'


class InstalledProduct(CommonInfo):
    """Copy of SF Installed Product Object"""
    product_description_c = models.TextField(
        max_length=4000,
        null=True,
        blank=True)

    class Meta:
        """Django Meta options"""
        db_table = 'installedproduct'


class SFUser(CommonInfo):
    """Copy of SF user Object"""
    sso_c = models.CharField(
        max_length=80,
        null=True,
        blank=True)
    manager = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False)

    class Meta:
        """Django Meta options"""
        db_table = 'sfuser'


class ServiceGroupMembers(CommonInfo):
    """Copy of SF technician Object"""
    svmxc_email_c = models.EmailField(
        max_length=80,
        null=True,
        blank=True)
    svmxc_salesforce_user_c = models.ForeignKey(
        SFUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False)

    class Meta:
        """Django Meta options"""
        db_table = 'servicegroupmembers'


class ServiceOrder(CommonInfo):
    """Copy of SF work order Object"""
    binder_date_acknowledged_c = models.DateField(
        null=True,
        blank=True)
    case_spr_number_c = models.TextField(
        max_length=1300,
        null=True,
        blank=True)
    hcls_cor_req_comp_dt_c = models.DateTimeField(
        null=True,
        blank=True)
    recordtypeid = models.CharField(
        max_length=18,
        null=True,
        blank=True)
    svmxc_actual_restoration_c = models.DateTimeField(
        null=True,
        blank=True)
    svmxc_case_c = models.ForeignKey(
        Case,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    svmxc_company_c = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    svmxc_completed_date_time_c = models.DateTimeField(
        null=True,
        blank=True)
    svmxc_component_c = models.ForeignKey(
        InstalledProduct,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    svmxc_contact_c = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    svmxc_country_c = models.CharField(
        max_length=255,
        null=True,
        blank=True)
    svmxc_group_member_c = models.ForeignKey(
        ServiceGroupMembers,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    svmxc_order_type_c = models.CharField(
        max_length=255,
        null=True,
        blank=True)

    class Meta:
        """Django Meta options"""
        db_table = 'serviceorder'
