from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Customer)
admin.site.register(Debt)
admin.site.register(DebtInstallment)
admin.site.register(DebtContent)
