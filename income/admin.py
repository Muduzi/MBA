from django.contrib import admin
from .models import *
# Register your models here.

#products.
admin.site.register(ProductIncome)
admin.site.register(IncomeBuffer)
admin.site.register(Invoice)
admin.site.register(InvoiceItems)
admin.site.register(ProductGeneralContent)

#services
admin.site.register(Category)
admin.site.register(Service)
admin.site.register(Package)
admin.site.register(PackageServices)
admin.site.register(ServiceIncome)
admin.site.register(ServiceBuffer)
admin.site.register(ServiceGeneralContent)
admin.site.register(ServiceAnnualContent)
admin.site.register(ServiceMonthlyContent)
