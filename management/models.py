from django.db import models
from django.contrib.auth.models import User
from User.models import Business
# Create your models here.


class Features(models.Model):
    Name = models.CharField(null=False, max_length=100)


class TermAndConditionsAgreements(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)


class SubscriptionPlan(models.Model):
    packages = [('Basic', 'Basic'),
                ('Standard', 'Standard'),
                ('Advanced', 'Advanced'),
                ('Premium', 'Premium')]
    Name = models.CharField(null=False, choices=packages, max_length=20, default='Bronze')
    Price = models.IntegerField(null=False)


class PlanFeatures(models.Model):
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, null=True)
    feature = models.ForeignKey(Features, on_delete=models.CASCADE, null=True)


class Subscription(models.Model):
    DatePaid = models.DateTimeField(auto_now=True)
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, null=True)
    Start = models.DateTimeField(null=False)
    End = models.DateTimeField(null=False)
    status = [('Active', 'Active'),
              ('Inactive', 'Inactive'),
              ('Pending', 'Pending')]
    Status = models.CharField(null=False, choices=status, max_length=9, default='Inactive')


# Taxes

# Value added tax

class ValueAddedTax(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, blank=True, max_length=50, default='VAT')
    Status = models.BooleanField(null=False, blank=True, default=True)
    Threshold = models.IntegerField(null=False, blank=False, default=0)
    Rate = models.IntegerField(null=False, blank=False, default=16.5)


class IncomeTax(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, blank=True, max_length=50, default='PAYE')
    Notes = models.CharField(null=True, blank=True, max_length=200, default='')
    Status = models.BooleanField(null=False, blank=True, default=True)


class IncomeTaxThreshold(models.Model):
    Tax = models.ForeignKey(IncomeTax, on_delete=models.CASCADE, null=False)
    Threshold = models.IntegerField(null=False, blank=False, default=0)
    Percentage = models.IntegerField(null=False, blank=False, default=0)


# pay as you earn tax
class PayAsYouEarn(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, blank=True, max_length=50, default='PAYE')
    Notes = models.CharField(null=True, blank=True, max_length=200, default='')
    Status = models.BooleanField(null=False, blank=True, default=True)


class PayAsYouEarnThreshold(models.Model):
    Tax = models.ForeignKey(PayAsYouEarn, on_delete=models.CASCADE, null=False)
    Threshold = models.IntegerField(null=False, blank=False, default=0)
    Percentage = models.IntegerField(null=False, blank=False, default=0)


# Presumptive tax
class PresumptiveTax(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, blank=True, max_length=50, default='Presumptive')
    Notes = models.CharField(null=True, blank=True, max_length=200, default='')
    Status = models.BooleanField(null=False, blank=True, default=True)


class PresumptiveTaxThreshold(models.Model):
    Tax = models.ForeignKey(PresumptiveTax, on_delete=models.CASCADE, null=False)
    From = models.IntegerField(null=False, blank=False, default=0)
    To = models.IntegerField(null=False, blank=False, default=0)
    Amount = models.IntegerField(null=False, blank=False, default=0)


