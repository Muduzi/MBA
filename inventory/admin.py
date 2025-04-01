from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(InventoryCategory)
admin.site.register(InventoryProduct)
admin.site.register(InventoryProductInfo)
admin.site.register(InventoryDraft)
