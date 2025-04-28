from django.db import models
from django.contrib.auth.models import User
from User.models import Business
# Create your models here.


class Features(models.Model):
    Name = models.CharField(null=False, max_length=100)


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
