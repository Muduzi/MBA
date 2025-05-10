from django.contrib import admin
from .models import *
# Register your models here.


admin.site.register(CatalogueCategories)
admin.site.register(CatalogueProduct)
admin.site.register(CatalogueProductPhoto)
admin.site.register(CatalogueProductFeature)
admin.site.register(Followers)
admin.site.register(LikeProduct)
admin.site.register(UnLikeProduct)
admin.site.register(Comments)
admin.site.register(LikeComment)
admin.site.register(UnLikeComment)
