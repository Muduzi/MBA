from django.db import models
from User.models import Business
# Create your models here.


class Customer(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False, blank=False,)
    date = models.DateTimeField(auto_now=True)
    Name = models.CharField(blank=False, null=False, max_length=40)
    Email = models.EmailField(null=True, blank=True)
    Contact = models.CharField(blank=False, null=False, max_length=13)
    Notes = models.TextField(blank=True, null=True, max_length=250)


class Debt(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Options = [
        ('Paying', 'Paying'),
        ('Paid', 'Paid'),
        ('Not Paid', 'Not Paid'),
    ]
    Date = models.DateTimeField(auto_now=True)
    Customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    Amount = models.IntegerField(blank=True, null=False, default=0)
    Due = models.DateTimeField(null=True, blank=True)
    Status = models.CharField(max_length=13, choices=Options, default='Not Paid')
    Received = models.IntegerField(null=False, default=0, blank=True)
    Notes = models.TextField(blank=True, null=True, max_length=150)


class DebtInstallment(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Debt = models.ForeignKey(Debt, on_delete=models.CASCADE, blank=True, null=True)
    Date = models.DateTimeField(auto_now=True)
    Amount = models.IntegerField(null=False, default=0, blank=True)
