from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Business)
admin.site.register(Profile)
admin.site.register(Department)
admin.site.register(Employee)
admin.site.register(Salary)
admin.site.register(EmployeeAllowance)
admin.site.register(Allowance)
admin.site.register(EmployeeIncentives)
admin.site.register(TaxYear)
admin.site.register(TaxAccount)
admin.site.register(TaxAccountThisYear)
admin.site.register(TaxInstallments)
admin.site.register(TaxSettings)
admin.site.register(CoreSettings)
admin.site.register(CashAccount)
admin.site.register(BusinessDashContent)

