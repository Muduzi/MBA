from django.db import models
from User.models import Business
from expenses.models import Expense
# Create your models here.


class InventoryCategory(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)
    Name = models.CharField(null=False, max_length=30)
    Notes = models.CharField(null=True, max_length=200)


class InventoryProduct(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)
    Expenses = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    Category = models.ForeignKey(InventoryCategory, on_delete=models.CASCADE, null=False)
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, max_length=30)
    Brand = models.CharField(null=False, max_length=30)
    Size = models.CharField(null=False, max_length=15)
    ExpiryDate = models.DateTimeField(null=True)


class InventoryProductInfo(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)
    Product = models.OneToOneField(InventoryProduct, on_delete=models.CASCADE, null=False)
    Code = models.CharField(null=False, max_length=30, default='')
    Location = models.CharField(null=True, max_length=30)
    Cost = models.IntegerField(null=False, default=0)
    BPrice = models.IntegerField(null=False, default=0)
    SPrice = models.IntegerField(null=False, default=0)
    InitialQuantity = models.IntegerField(null=False, default=0)
    CurrentQuantity = models.IntegerField(null=False, default=0)
    InitialValue = models.IntegerField(null=False, default=0)
    CurrentValue = models.IntegerField(null=False, default=0)
    ReorderPerc = models.IntegerField(null=False, default=50)
    Close = models.BooleanField(null=False, default=False)


class InventoryDraft(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=False)
    Expenses = models.ForeignKey(Expense, on_delete=models.CASCADE, null=False)
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, max_length=30)
    InitialQuantity = models.IntegerField(null=False, default=0)
    Cost = models.IntegerField(null=False, default=0)







