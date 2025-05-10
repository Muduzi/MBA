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
    User = models.ForeignKey(User, null=True, on_delete=models.CASCADE)


class LikeProduct(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Product = models.ForeignKey(CatalogueProduct, on_delete=models.CASCADE, blank=True, null=True)
    User = models.ForeignKey(User, null=True, on_delete=models.CASCADE)


class UnLikeProduct(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Product = models.ForeignKey(CatalogueProduct, on_delete=models.CASCADE, blank=True, null=True)
    User = models.ForeignKey(User, null=True, on_delete=models.CASCADE)


class Comments(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Product = models.ForeignKey(CatalogueProduct, on_delete=models.CASCADE, null=False, blank=False)
    User = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    Root = models.ForeignKey('self', null=True, on_delete=models.CASCADE, related_name='trailRoot')
    Comment = models.CharField(max_length=500, null=False, blank=False)


class LikeComment(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Comment = models.ForeignKey(Comments, on_delete=models.CASCADE, blank=True, null=True)
    User = models.ForeignKey(User, null=True, on_delete=models.CASCADE)


class UnLikeComment(models.Model):
    Date = models.DateTimeField(auto_now=True)
    Comment = models.ForeignKey(Comments, on_delete=models.CASCADE, blank=True, null=True)
    User = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
