from django.db import models
from User.models import User, Business

# Create your models here.


class Supplier(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False, blank=False)
    date = models.DateTimeField(auto_now=True)
    Name = models.CharField(blank=False, null=False, max_length=40)
    Email = models.EmailField(null=True, blank=True)
    Contact = models.CharField(blank=False, null=False)
    Notes = models.TextField(blank=True, null=True, max_length=250)


class Credit(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Options = [
        ('Paying', 'Paying'),
        ('Paid', 'Paid'),
        ('Not Paid', 'Not Paid'),
    ]
    Date = models.DateTimeField(auto_now=True)
    Supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, blank=True, null=False)
    Amount = models.IntegerField(blank=True, null=False, default=0)
    Due = models.DateTimeField(null=True, blank=True)
    Status = models.CharField(max_length=13, choices=Options, default='Not Paid')
    Sent = models.IntegerField(null=False, default=0, blank=True)
    Notes = models.TextField(blank=True, null=True, max_length=250)


class CreditInstallment(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Credit = models.ForeignKey(Credit, on_delete=models.CASCADE, blank=True, null=True)
    Date = models.DateTimeField(auto_now=True)
    Amount = models.IntegerField(null=False, default=0, blank=True)


class CreditContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('All', 'All'),
        ('Current', 'Current'),
    ]
    Choice = models.CharField(max_length=11, choices=options, default='This Month', null=False)

