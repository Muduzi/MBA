from django.db import models
from User.models import User, Business
from debts.models import Debt, Customer
from datetime import datetime
from inventory.models import InventoryProduct
# Create your models here.


# product income
class ProductIncome(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Options = [
        ('Cash', 'Cash'),
        ('Credit', 'Credit'),
    ]
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=False, null=True)
    Debt = models.ForeignKey(Debt, on_delete=models.DO_NOTHING, null=True, blank=True)
    Product = models.ForeignKey(InventoryProduct, on_delete=models.DO_NOTHING, null=True)
    Date = models.DateTimeField(auto_now=True, null=True)
    Code = models.CharField(null=False, max_length=30, default='')
    Amount = models.IntegerField(blank=False, null=False)
    Quantity = models.IntegerField(default=1, blank=False, null=False)
    PMode = models.CharField(max_length=7, choices=Options, default='Cash', blank=False, null=False)
    Discount = models.BooleanField(null=False, blank=True, default=False)


class IncomeBuffer(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=False, null=True)
    Product = models.ForeignKey(InventoryProduct, on_delete=models.DO_NOTHING, null=True)
    Date = models.DateTimeField(auto_now=True)
    Code = models.CharField(null=False, max_length=30, default='')
    Amount = models.IntegerField(blank=False, null=False)
    Quantity = models.IntegerField(default=1, blank=False, null=False)


"""Product Content Settings"""


class ProductGeneralContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('This Year', 'This Year'),
        ('This Month', 'This Month'),
    ]
    Choice = models.CharField(max_length=11, choices=options, default='This Month', null=False)


#Service models

class Category(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False, blank=False)
    Name = models.CharField(null=False, blank=False, max_length=30)
    Notes = models.TextField(null=True, blank=True, max_length=200)


class Package(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False, blank=False)
    Date = models.DateTimeField(auto_now=True)
    Category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False, blank=False)
    Name = models.CharField(null=False, blank=False, max_length=50, default='')
    Price = models.IntegerField(null=False, blank=True, default=0)


class Service(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False, blank=False)
    Date = models.DateTimeField(auto_now=True)
    Category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False, blank=False)
    Name = models.CharField(null=False, blank=False, max_length=50, default='')
    Description = models.TextField(null=False, blank=False, max_length=200)
    options = [('per specified duration', 'per specified duration'),
               ('per srvice', 'per service'),
               ('agreed condition', 'agreed condition')
               ]
    ChargingCriteria = models.CharField(choices=options, null=False, blank=True, max_length=25, default='per service')
    Price = models.IntegerField(null=False, blank=True, default=0)


class PackageServices(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Package = models.ForeignKey(Package, on_delete=models.DO_NOTHING, null=True, blank=True)
    Service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, null=True)


class ServiceIncome(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=False)
    Customer = models.ForeignKey(Customer, on_delete=models.DO_NOTHING, null=True, blank=True)
    Debt = models.ForeignKey(Debt, on_delete=models.DO_NOTHING, null=True, blank=True)
    Date = models.DateTimeField(auto_now=True)
    Package = models.ForeignKey(Package, on_delete=models.DO_NOTHING, null=True)
    Service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, null=True)
    Quantity = models.IntegerField(null=False, default=1)
    Amount = models.IntegerField(null=False, default=0)
    Options = [
        ('Cash', 'Cash'),
        ('Credit', 'Credit'),
    ]
    PMode = models.CharField(max_length=7, choices=Options, default='Cash', null=False)


class ServiceBuffer(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=False)
    Date = models.DateTimeField(auto_now=True)
    Package = models.ForeignKey(Package, on_delete=models.DO_NOTHING, null=True)
    Service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, null=True)
    Quantity = models.IntegerField(null=False, default=1)
    Amount = models.IntegerField(null=False, default=1)
    Options = [
        ('Cash', 'Cash'),
        ('Credit', 'Credit'),
    ]
    PMode = models.CharField(max_length=7, choices=Options, default='Cash', null=False)


"""Invoice"""


class Invoice(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=False, null=True)
    Receiver = models.ForeignKey(Customer, on_delete=models.DO_NOTHING, null=True, blank=True)
    Date = models.DateTimeField(auto_now=True, null=True)
    OrderNumber = models.IntegerField(null=False, default=0)
    DispatchDate = models.DateTimeField(null=True)
    ValidityLimit = models.DateTimeField(null=True)
    GrandTotal = models.IntegerField(null=False, default=0)
    VAT = models.FloatField(null=False, default=0)
    SubTotal = models.IntegerField(null=False, default=0)
    Status = models.BooleanField(null=False, default=False)


class InvoiceItems(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, blank=False, null=True)
    Product = models.ForeignKey(InventoryProduct, on_delete=models.DO_NOTHING, null=True)
    Package = models.ForeignKey(Package, on_delete=models.DO_NOTHING, null=True)
    Service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, null=True)
    UnitPrice = models.IntegerField(blank=False, null=False)
    Quantity = models.IntegerField(default=1, blank=False, null=False)
    Total = models.IntegerField(blank=False, null=False)


"""Service Content Settings"""


class ServiceGeneralContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('This Year', 'This Year'),
        ('This Month', 'This Month'),
    ]
    Choice = models.CharField(max_length=11, choices=options, default='This Month', null=False)


class ServiceMonthlyContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('Categories', 'Categories'),
        ('Service', 'Service'),
        ('Packages', 'Packages')
    ]
    Choice = models.CharField(max_length=17, choices=options, default='Service/Packages', null=False)


class ServiceAnnualContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('Categories', 'Categories'),
        ('Service', 'Service'),
        ('Packages', 'Packages')
    ]
    Choice = models.CharField(max_length=17, choices=options, default='Service/Packages', null=False)
