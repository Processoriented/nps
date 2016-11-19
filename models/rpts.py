from django.db import models
from .general import ForceAPI


class Report_Def(models.Model):
    name = models.CharField(
        max_length=80)
    description = models.TextField(
        null=True,
        blank=True)

    def __str__(self):
        return self.name


class Rest_Source(models.Model):
    name = models.CharField(max_length=80)
    credentials = models.ForeignKey(
        ForceAPI,
        on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class DataBase_Source(models.Model):
    name = models.CharField(max_length=80)
    connection_string = models.TextField(
        null=True,
        blank=True)

    def __str__(self):
        return self.name


class Report_Source(models.Model):
    report = models.ForeignKey(
        Report_Def,
        on_delete=models.CASCADE)
    rest_source = models.ForeignKey(
        Rest_Source,
        on_delete=models.CASCADE,
        null=True)
    db_source = models.ForeignKey(
        DataBase_Source,
        on_delete=models.CASCADE,
        null=True)
    query_string = models.TextField(
        null=True,
        blank=True)

    def __str__(self):
        return "%s Source %s (%s)" %
            self.report.name,
            