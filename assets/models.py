from django.db import models
from User.models import Business, TaxYear
from django.contrib.auth.models import User
from expenses.models import Expense


class Assets(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    TaxYear = models.ForeignKey(TaxYear, on_delete=models.CASCADE, blank=True, null=True)
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(blank=False, null=False, max_length=40)
    InitialValue = models.IntegerField(blank=False, null=False, default=0)
    CurrentValue = models.IntegerField(blank=False, null=False, default=0)
    DepreciationRate = models.IntegerField(blank=False, null=False, default=0)
    AnnualDepreciation = models.IntegerField(blank=False, null=False, default=0)
    SalvageValue = models.IntegerField(blank=False, null=False, default=0)
    UsefulLife = models.IntegerField(blank=False, null=False, default=0)
    Notes = models.TextField(blank=False, null=False, max_length=200, default='non')


class AssetSpecification(models.Model):
    Asset = models.ForeignKey(Assets, on_delete=models.CASCADE, blank=True, null=False)
    Date = models.DateTimeField(auto_now=True)
    Title = models.CharField(null=False, max_length=20)
    Description = models.TextField(null=False, max_length=100, default='')


class AssetPhotos(models.Model):
    Asset = models.ForeignKey(Assets, on_delete=models.CASCADE, blank=True, null=False)
    Date = models.DateTimeField(auto_now=True)
    Photo = models.ImageField(null=False, upload_to='asset', width_field=None, height_field=None)


class AssetsBuffer(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Name = models.CharField(blank=False, null=False, max_length=25)
    Quantity = models.IntegerField(default=1, blank=False, null=False)
    InitialValue = models.IntegerField(blank=False, null=False)
    options = [('Purchase(cash)', 'Purchase(cash)'),
               ('Purchase(debts)', 'Purchase(debts)'),
               ('Donation', 'Donation')
               ]
    Acquired_through = models.CharField(max_length=18, choices=options, default='Purchase(cash)', blank=False, null=False)
    SalvageValue = models.IntegerField(blank=False, null=False, default=0)
    UsefulLife = models.IntegerField(blank=False, null=False, default=0)
    Notes = models.TextField(blank=False, null=False, max_length=30, default='non')
