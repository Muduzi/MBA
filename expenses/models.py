from django.db import models
from User.models import User, Business, Salary
from credits.models import Credit, Supplier
# Create your models here.

options = [
        ('Cash', 'Cash'),
        ('Credit', 'Credit'),
    ]

Option = [('Operational', 'Operational'),
          ('Payroll', 'Payroll'),
          ('Stock', 'Stock'),
          ('Asset', 'Asset')]


class ExpenseAccount(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Date = models.DateTimeField(auto_now=True)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=False, null=True)
    Name = models.CharField(blank=False, null=False, max_length=20)
    Type = models.CharField(blank=False, null=False, max_length=20, choices=Option, default='Operational Expense')
    intervals = [
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
        ('Annually', 'Annually')
    ]
    Interval = models.CharField(choices=options, null=False, blank=True, max_length=9, default='Monthly')
    AutoRecord = models.BooleanField(null=False, blank=True, default=False)
    Notes = models.TextField(blank=False, null=False, max_length=150, default='non')


class Expense(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Supplier = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING, blank=True, null=True)
    Credit = models.ForeignKey(Credit, on_delete=models.DO_NOTHING, blank=True, null=True)
    Salary = models.ForeignKey(Salary, on_delete=models.CASCADE, blank=True, null=True)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=False, null=True)
    ExpenseAccount = models.ForeignKey(ExpenseAccount, on_delete=models.DO_NOTHING, null=True, blank=True)
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(blank=False, null=False, max_length=20)
    Price = models.IntegerField(blank=False, null=False)
    Quantity = models.IntegerField(default=1, blank=False, null=False)
    Type = models.CharField(blank=False, null=False, max_length=20, choices=Option, default='Operational Expense')
    PMode = models.CharField(blank=False, null=False, max_length=7, choices=options, default='Cash')
    Discount = models.BooleanField(blank=False, null=False, default=0)
    Notes = models.TextField(blank=True, null=True, max_length=150, default='non')


class Discount(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Expense = models.ForeignKey(Expense, on_delete=models.CASCADE, blank=True, null=True)
    OriginalPrice = models.IntegerField(blank=False, null=False)
    DiscountPrice = models.IntegerField(blank=False, null=False)
    Notes = models.TextField(blank=False, null=False, max_length=30, default='non')


class BufferExpense(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Cashier = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=False)
    ExpenseAccount = models.ForeignKey(ExpenseAccount, on_delete=models.DO_NOTHING, null=True, blank=True)
    Type = models.CharField(blank=False, null=False, max_length=20, choices=Option, default='Operational')
    Name = models.CharField(blank=False, null=False, max_length=20)
    Quantity = models.IntegerField(default=1, blank=False, null=False)
    Price = models.IntegerField(blank=False, null=False)
    PMode = models.CharField(blank=False, null=False, max_length=7, choices=options, default='Cash')
    Discount = models.BooleanField(blank=False, null=False, default=False)
    Notes = models.TextField(blank=False, null=False, max_length=150, default='non')


class ExpensesGeneralContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('This Year', 'This Year'),
        ('This Month', 'This Month'),
    ]
    Choice = models.CharField(max_length=11, choices=options, default='This Month', null=False)
