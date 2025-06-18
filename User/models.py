from django.db import models
from datetime import datetime
# Create your models here.
from django.contrib.auth.models import User, Group
# Create your models here.


class Profile(models.Model):
    User = models.OneToOneField(User, null=False, on_delete=models.CASCADE)
    Date = models.DateTimeField(auto_now=True)
    Options = [
        ('Male', 'Male'),
        ('Female', 'Female')
    ]
    Gender = models.CharField(null=True, choices=Options, max_length=8, default='Female')
    DOB = models.DateField(null=True)
    Photo = models.ImageField(null=True, upload_to='profile', width_field=None, height_field=None)
    About = models.TextField(null=True, blank=True, max_length=130)
    Contact1 = models.CharField(null=True, max_length=15)
    Contact2 = models.CharField(blank=True, null=True, max_length=15)
    City = models.CharField(null=True, max_length=50)
    Country = models.CharField(null=True, max_length=50)
    Instagram = models.CharField(null=True, blank=True, max_length=100)
    Facebook = models.CharField(null=True, blank=True, max_length=100)
    Linkedin = models.CharField(null=True, blank=True, max_length=100)
    options = [
        ('Business', 'Business'),
        ('Work', 'Work'),
        ('Buying', 'Buying')
    ]
    Role = models.CharField(null=True, blank=True, max_length=7, default='Buyer')


class Business(models.Model):
    options = [
        ('Groceries', 'Groceries'),
        ('School & Office supplies', 'School & Office supplies'),
        ('Fashion(Apparel, shoes, Jewerly)', 'Fashion(Apparel, shoes, Jewerly)'),
        ('Cosmetics', 'Cosmetics'),
        ('Furniture', 'Furniture'),
        ('Home appliances', 'Home appliances'),
        ('Consumer Electronics', 'Consumer Electronics'),
        ('Security & Safety', 'Security & Safety'),
        ('Cars, spare parts & accessories', 'Cars, spare parts & accessories'),
        ('Construction', 'Construction'),
        ('Tools & Hardware', 'Tools & Hardware'),
        ('Farm equipment & chemicals', 'Farm equipment & chemicals'),
        ('Health & Personal Care', 'Health & Personal Care'),
        ('Hotel and Lodging', 'Hotel and Lodging'),
        ('Food & Beverages', 'Food & Beverages'),
        ('Entertainment', 'Entertainment'),
        ('Sports', 'Sports'),
        ('Real Estate', 'Real Estate'),
    ]
    Owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    Date = models.DateTimeField(auto_now=True)
    Photo = models.ImageField(null=False, blank=True, upload_to='bprofile', default='/appdefaults/add-photo4.png', width_field=None, height_field=None)
    Name = models.CharField(blank=False, null=False, max_length=50)
    Type = models.CharField(null=False, blank=True, max_length=33, default='Groceries')
    About = models.TextField(blank=False, null=False, max_length=110)
    Email = models.EmailField(null=False, blank=False)
    Contact1 = models.CharField(blank=True, null=True, max_length=15)
    Contact2 = models.CharField(blank=True, null=True, max_length=15)
    Address = models.CharField(blank=False, null=False, max_length=150)
    PostBox = models.CharField(blank=False, null=False, max_length=50, default='')
    City = models.CharField(null=False, blank=False, max_length=50)
    Country = models.CharField(null=False, blank=False, max_length=50)
    ZipCode = models.CharField(null=True, blank=True, max_length=50)
    Instagram = models.CharField(null=True, blank=True, max_length=100)
    Facebook = models.CharField(null=True, blank=True, max_length=100)
    Linkedin = models.CharField(null=True, blank=True, max_length=100)


# Settings
class TaxYear(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=False)
    TaxYearStart = models.DateTimeField(null=False, blank=True)
    TaxYearEnd = models.DateTimeField(null=False, blank=True)
    TotalTaxes = models.IntegerField(null=False, blank=True, default=0)
    TotalPaid = models.IntegerField(null=False, blank=True, default=0)


class TaxAccount(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=False)
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, blank=True, max_length=40)
    options = [('Monthly', 'Monthly'),
               ('Quarterly', 'Quarterly'),
               ('Annually', 'Annually')]
    Interval = models.CharField(null=False, blank=False, choices=options, max_length=17, default='Monthly')
    Notes = models.TextField(blank=False, null=False, max_length=200, default='non')
    Close = models.BooleanField(null=True, blank=True, default=False)


class TaxAccountThisYear(models.Model):
    TaxAccount = models.ForeignKey(TaxAccount, on_delete=models.CASCADE, blank=True, null=False)
    TaxYear = models.ForeignKey(TaxYear, on_delete=models.CASCADE, blank=True, null=False)
    AccumulatedTotal = models.IntegerField(null=False, blank=True, default=0)


class TaxInstallments(models.Model):
    Date = models.DateTimeField(auto_now=True)
    TaxAccountThisYear = models.ForeignKey(TaxAccountThisYear, on_delete=models.CASCADE, blank=True, null=True)
    Amount = models.IntegerField(blank=False, null=False)


class TaxSettings(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    VATRate = models.FloatField(null=False, default=16.5)
    ShowEstimates = models.BooleanField(blank=False, null=False, default=0)
    IncludeVAT = models.BooleanField(blank=False, null=False, default=0)
    IncludePAYE = models.BooleanField(blank=False, null=False, default=0)
    IncludePresumptiveTax = models.BooleanField(blank=False, null=False, default=0)
    IncludeIncomeTax = models.BooleanField(blank=False, null=False, default=0)


class CoreSettings(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Capital = models.IntegerField(blank=False, null=False, default=0)
    StartBusinessYear = models.DateTimeField(null=True, blank=True)


class CashAccount(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Value = models.IntegerField(blank=False, null=False, default=0)
    TotalShares = models.IntegerField(blank=False, null=False, default=100)
    PayoutRatio = models.IntegerField(blank=False, null=False, default=20)


# Departments and Employees
class Department(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    date_of_creation = models.DateTimeField(auto_now=True)
    Name = models.CharField(blank=False, null=False, max_length=40)
    Description = models.TextField(blank=False, null=False, max_length=300)
    Head = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)


class Employee(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    User = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    Department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True)
    Position = models.CharField(blank=False, null=False, max_length=40, default='')
    AccessLevel = models.ForeignKey(Group, on_delete=models.CASCADE, blank=True, null=True)
    Duty = models.CharField(max_length=200, null=False, blank=False, default='')
    options = [('Monthly', 'Monthly'),
               ('Weekly', 'Weekly'),
               ('Daily', 'Daily'),
               ('Hourly', 'Hourly'),
               ('Agreed Condition', 'Agreed Condition')]
    Interval = models.CharField(null=False, blank=False, choices=options, max_length=17, default='Monthly')
    Salary = models.IntegerField(null=False, default=0)


class Salary(models.Model):
    Date = models.DateTimeField(auto_now=True)
    TaxAccountThisYear = models.ForeignKey(TaxAccountThisYear, on_delete=models.CASCADE, blank=True, null=True)
    Employee = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True)
    Amount = models.IntegerField(null=False, default=0)
    PAYE = models.IntegerField(null=False, default=0)


class EmployeeAllowance(models.Model):
    Employee = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True)
    Name = models.CharField(null=False, blank=False, max_length=30)
    options = [('Monthly', 'Monthly'),
               ('Weekly', 'Weekly'),
               ('Daily', 'Daily'),
               ('Agreed Condition', 'Agreed Condition')]
    Interval = models.CharField(null=False, blank=False, choices=options, max_length=17)
    Amount = models.IntegerField(null=False, default=0)


class Allowance(models.Model):
    Date = models.DateTimeField(auto_now=True)
    TaxAccountThisYear = models.ForeignKey(TaxAccountThisYear, on_delete=models.CASCADE, blank=True, null=True)
    EmployeeAllowance = models.ForeignKey(EmployeeAllowance, on_delete=models.CASCADE, blank=True, null=True)
    Amount = models.IntegerField(null=False, default=0)
    PAYE = models.IntegerField(null=False, default=0)


class EmployeeIncentives(models.Model):
    Date = models.DateTimeField(auto_now=True)
    TaxAccountThisYear = models.ForeignKey(TaxAccountThisYear, on_delete=models.CASCADE, blank=True, null=True)
    Employee = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True)
    Name = models.CharField(null=False, blank=False, max_length=30)
    Amount = models.IntegerField(null=False, default=0)
    PAYE = models.IntegerField(null=False, default=0)


# Business dash settings
class BusinessDashContent(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True)
    Cashier = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    options = [
        ('This Year', 'This Year'),
        ('This Month', 'This Month'),
    ]
    Choice = models.CharField(max_length=17, choices=options, default='This Year', null=False)
