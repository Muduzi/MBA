from django.db import models
from User.models import Business
from django.contrib.auth.models import User
# Create your models here.


class CatalogueCategories(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Name = models.CharField(null=False, blank=False, max_length=20)
    Photo = models.ImageField(null=True, blank=False, upload_to='catalogue', width_field=None, height_field=None)


class CatalogueProduct(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Category = models.ForeignKey(CatalogueCategories, on_delete=models.CASCADE, blank=True, null=False, default='')
    Date = models.DateTimeField(auto_now=True)
    Name = models.CharField(null=False, max_length=20)
    Price = models.IntegerField(null=False, default=0)
    Description = models.TextField(null=False, max_length=160)


class CatalogueProductPhoto(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Product = models.ForeignKey(CatalogueProduct, on_delete=models.CASCADE, blank=True, null=True)
    Photo = models.ImageField(null=False, upload_to='catalogue', width_field=None, height_field=None)


class CatalogueProductFeature(models.Model):
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    Product = models.ForeignKey(CatalogueProduct, on_delete=models.CASCADE, blank=True, null=True)
    Name = models.CharField(null=False, max_length=20)
    Description = models.TextField(null=False, max_length=100, default='')


class Followers(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Business = models.ForeignKey(Business, on_delete=models.CASCADE, blank=True, null=True)
    User = models.OneToOneField(User, null=True, on_delete=models.CASCADE)


class Likes(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Product = models.ForeignKey(CatalogueProduct, on_delete=models.CASCADE, blank=True, null=True)
    User = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
