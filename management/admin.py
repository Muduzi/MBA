from django.contrib import admin
from .models import *
# Register your models here.


admin.site.register(SubscriptionPlan)
admin.site.register(Features)
admin.site.register(PlanFeatures)
admin.site.register(Subscription)
admin.site.register(ValueAddedTax)
admin.site.register(IncomeTax)
admin.site.register(PayAsYouEarn)
admin.site.register(PayAsYouEarnThreshold)
admin.site.register(PresumptiveTax)
admin.site.register(PresumptiveTaxThreshold)
