import random

from django.shortcuts import render, redirect, HttpResponse
from catalogue.models import (CatalogueCategories, CatalogueProduct, CatalogueProductPhoto, CatalogueProductFeature,
                              Followers)
from User.models import Employee, Business
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models.functions import Random
from User.decorator import allowed_users
from inventory.models import InventoryCategory
from fuzzywuzzy import fuzz, process
from django.contrib import messages
from django.db.models import Q
import time
from django.contrib.gis.geoip2 import GeoIP2
from django.core.cache import cache
from celery import shared_task
# Create your views here.


def products_in_categories():
    options = [
        'Groceries',
        'School & Office supplies',
        'Fashion(Apparel, shoes, Jewerly)',
        'Cosmetics',
        'Furniture',
        'Home appliances',
        'Consumer Electronics',
        'Security & Safety',
        'Cars, spare parts & accessories',
        'Construction',
        'Tools & Hardware',
        'Farm equipment & chemicals',
        'Health & Personal Care',
        'Hotel and Lodging',
        'Food & Beverages',
        'Entertainment',
        'Sports', 'Sports',
        'Real Estate'
    ]
    shuffle_list = []
    categories = {}
    images = []
    for i in options:
        businesses = Business.objects.filter(Type=i).order_by(Random())
        if businesses.exists():
            selected_business = businesses[0].id

            content = CatalogueProduct.objects.filter(Business__id=selected_business).order_by('id')
            if content:
                if len(content) > 4:
                    content = list(content)[:4]
                categories[i] = []
                for c in content:
                    print(c.Name, c.id)
                    img = CatalogueProductPhoto.objects.filter(Product=c.id)
                    for p in img:
                        images.append(p.Photo)
                        random.shuffle(images)
                    example = {'Business': c.Business, 'Name': c.Name, 'Price': c.Price, 'Photo': images[0]}
                    categories[i].append(example)
                    images = []
    return categories


def query_item_by_letter1(lookup_word):
    """
    search1 = Products.objects.filter(Q(name__icontains=lookup_word))
    search2 = Categories.objects.filter(Q(name__icontains=lookup_word))
    """
    match1 = []
    match2 = []
    img_li = []
    photo = None
    lookup1 = CatalogueProduct.objects.all()
    for i in lookup1:
        img_li = []
        ratio = fuzz.partial_ratio(lookup_word.lower(), i.Name.lower())

        if ratio > 60:
            try:
                photos = CatalogueProductPhoto.objects.filter(Product=i.id)
                if photos:
                    for x in photos:
                        img_li.append(x.Photo)

                photo = img_li[0]
            except CatalogueProductPhoto.DoesNotExist:
                photos = None
            match1.append({'id': i.id, 'name': i.Name, 'photo': photo, 'ratio': ratio})
    search1 = sorted(match1, key=lambda x: x['ratio'], reverse=True)

    lookup2 = CatalogueCategories.objects.all()
    for i in lookup2:
        ratio = fuzz.partial_ratio(lookup_word.lower(), i.Name.lower())

        if ratio > 60:
            match2.append({'id': i.id, 'name': i.Name, 'photo': i.Photo, 'ratio': ratio})
    search2 = sorted(match2, key=lambda x: x['ratio'], reverse=True)

    return search1, search2


@shared_task()
def get_content(buss_type=''):
    content = []

    if buss_type != '':
        prod_obj = CatalogueProduct.objects.filter(Business__Type=buss_type).order_by('id')
    else:
        prod_obj = CatalogueProduct.objects.all().order_by('id')

    for i in prod_obj:
        picture_li = []
        photos = CatalogueProductPhoto.objects.filter(Product=i.id)
        if photos:
            for p in photos:
                picture_li.append(p.Photo)

        new_entry = {'store_name': i.Business.Name, 'store_photo': i.Business.Photo, 'product_id': i.id,
                     'product_name': i.Name, 'product_price': i.Price, 'product_photo': picture_li[0],
                     'product_description': i.Description}

        content.append(new_entry)

    cache.set(buss_type, content, 3600)
    return content


@shared_task()
def get_product(p_id):
    images = []
    bus_data = None
    prod_obj = None
    prod_photos_obj = None
    prod_features_obj = None

    try:
        prod_obj = CatalogueProduct.objects.get(pk=p_id)
        prod_photos_obj = CatalogueProductPhoto.objects.filter(Product=prod_obj.id)
        prod_features_obj = CatalogueProductFeature.objects.filter(Product=prod_obj.id)
        bus_data = Business.objects.get(pk=prod_obj.Business.id)

        for i in prod_photos_obj:
            images.append(i.Photo.url)

        cache.set('prod_obj'+str(p_id), prod_obj, 3600)
        cache.set('images'+str(p_id), images, 3600)
        cache.set('prod_features_obj'+str(p_id), prod_features_obj, 3600)
        cache.set('bus_data' + str(p_id), bus_data, 3600)

        return prod_obj, prod_photos_obj, prod_features_obj, bus_data
    except CatalogueProduct.DoesNotExist:
        return prod_obj, prod_photos_obj, prod_features_obj, bus_data


def market_view(request):
    content = None
    search1 = None
    search2 = None
    lookup_word = None
    try:
        client = User.objects.get(pk=request.user.id)
    except User.DoesNotExist:
        client = {}

    bus_types = {
        'School & Office supplies': 'books', 'Furniture': 'chair', 'Home appliances': 'tv',
        'Consumer Electronics': 'devices', 'Food & Beverages': 'liquor', 'Security & Safety': 'lock_open',
        'Cars, spare parts & accessories': 'car_repair', 'Construction': 'roofing', 'Tools & Hardware': 'handyman',
        'Farm equipment & chemicals': 'agriculture', 'Health & Personal Care': 'monitor_heart',
        'Hotel and Lodging': ' hotel', 'Entertainment': 'sports_kabaddi', 'Sports': 'sports_soccer',
        'Real Estate': 'real_estate_agent'
    }
    dict_size = len(bus_types)
    group_size = dict_size // 3

    group1 = dict(list(bus_types.items())[:group_size])
    group2 = dict(list(bus_types.items())[group_size:(group_size * 2)])
    group3 = dict(list(bus_types.items())[(group_size * 2):(group_size * 3)])

    get_content.delay('')
    data = cache.get('')

    if not data:
        data = get_content('')

    pages = Paginator(data, 5)

    if request.method == 'POST':
        if 'lookup_word' in request.POST:
            lookup_word = request.POST.get('lookup_word')
            search1, search2 = query_item_by_letter1(lookup_word)

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'close_search' in request.POST:
            if search1 and search2 or search1 or search2:
                search1 = None
                search2 = None

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'view_type' in request.POST:
            view_type = request.POST.get('view_type')
            view_type.replace(' ', '%')

            return redirect(f'/viewBusinessTypeProducts/{view_type}/')

    if request.method == 'GET':
        page_number = request.GET.get('page')
        content = pages.get_page(page_number)

    categories = products_in_categories()

    context = {
        'client': client,
        'content': content,
        'search1': search1,
        'search2': search2,
        'lookup_word': lookup_word,
        'billboard': categories,
        'group1': group1,
        'group2': group2,
        'group3': group3,
    }
    return render(request, 'market.html', context)


def query_item_by_letter(lookup_word):
    """
    search1 = Products.objects.filter(Q(name__icontains=lookup_word))
    search2 = Categories.objects.filter(Q(name__icontains=lookup_word))
    """
    match1 = []
    match2 = []
    lookup1 = CatalogueProduct.objects.all()
    for i in lookup1:
        ratio = fuzz.partial_ratio(lookup_word.lower(), i.Name.lower())

        if ratio > 60:
            match1.append({'id': i.id, 'ratio': ratio})
    search1 = sorted(match1, key=lambda x: x['ratio'], reverse=True)

    lookup2 = CatalogueCategories.objects.all()
    for i in lookup2:
        ratio = fuzz.partial_ratio(lookup_word.lower(), i.Name.lower())

        if ratio > 60:
            match2.append({'id': i.id, 'ratio': ratio})
    search2 = sorted(match2, key=lambda x: x['ratio'], reverse=True)

    return search1, search2


def catalogue_view(request, id=0):
    s_list = []
    categories = {}
    cat_obj = None
    buss = None
    prod_obj = None
    prod_photos_obj = None

    if id != 0:
        buss = Business.objects.get(pk=id)
        cat_obj = CatalogueCategories.objects.filter(Business=buss)
        prod_obj = CatalogueProduct.objects.filter(Business=buss)
        prod_photos_obj = CatalogueProductPhoto.objects.filter(Business=buss)

    else:
        try:
            check = Employee.objects.get(User=request.user.id)
            buss = check.Business
            staff_obj = Employee.objects.filter(Business=buss)
            for i in staff_obj:
                s_list.append(i.User)

            cat_obj = CatalogueCategories.objects.filter(Business=buss)
            prod_obj = CatalogueProduct.objects.filter(Business=buss)
            prod_photos_obj = CatalogueProductPhoto.objects.filter(Business=buss)

        except Employee.DoesNotExist:
            return redirect('/login/')

    for c in cat_obj:
        product_count = CatalogueProduct.objects.filter(Category=c).count()

        categories[c.id] = {}
        categories[c.id]['Name'] = c.Name
        categories[c.id]['Photo'] = c.Photo
        categories[c.id]['Count'] = product_count

    if request.method == 'POST':
        lookup_word = request.POST.get('lookup_word')

        search1, search2 = query_item_by_letter(lookup_word)
        if search1:
            for i in search1:
                return redirect(f"/view_product/{i['id']}/")
        elif search2:
            for i in search2:
                return redirect(f"/category/{i['id']}/")

    context = {
        'id': id,
        's_list': s_list,
        'bus_data': buss,
        'categories': categories,
        'prod_obj': prod_obj,
        'prod_photos_obj': prod_photos_obj
    }
    return render(request, 'catalogue.html', context)


@shared_task()
def get_category_product(category_id):
    products = []
    prod_obj = CatalogueProduct.objects.filter(Category__id=category_id)

    for i in prod_obj:
        product_image = []
        prod_photos_obj = CatalogueProductPhoto.objects.filter(Product__id=i.id)
        for x in prod_photos_obj:
            if x.Product == i:
                product_image.append(x.Photo)

        new_entry = {'id': i.id, 'Name': i.Name, 'Photo': product_image[0], 'Price': i.Price}
        products.append(new_entry)

    cache.set('categoryProduct' + str(category_id), products, 300)
    return products


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def add_category(request):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        inv = InventoryCategory.objects.filter(Business=buss)

        if request.method == 'POST':
            if 'create' in request.POST:
                name = request.POST.get("category name")
                image = request.FILES.get("category image")

                c = CatalogueCategories(Business=buss, Name=name, Photo=image)
                c.save()
                return redirect(f'/category/{c.id}/')

            elif 'selected' in request.POST:
                selected_id = request.POST.get("selected_id")
                image = request.FILES.get("category image")

                selected_id = int(selected_id)

                for i in inv:
                    if i.id == selected_id:
                        c = CatalogueCategories(Business=buss, Name=i.Name, Photo=image)
                        c.save()
                        return redirect(f'/category/{c.id}/')

    except Employee.DoesNotExist:
        return HttpResponse('Error *staff does not exist at create post* please contact developer')
    context = {
        'categories': inv
    }
    return render(request, 'addcategory.html', context)


def category(request, id=0):
    try:
        cat_obj = CatalogueCategories.objects.get(pk=id)

        bus_data = Business.objects.filter(pk=cat_obj.Business.id)

        get_category_product.delay(cat_obj.id)
        products = cache.get('categoryProduct' + str(cat_obj.id))
        if not products:
            products = get_category_product(cat_obj.id)

    except CatalogueCategories.DoesNotExist:
        return HttpResponse('Error *staff does not exist at create post* please contact developer')

    context = {
        'cat_obj': cat_obj,
        'bus_data': bus_data,
        'products': products,
    }
    return render(request, 'category.html', context)


def view_product(request, id=0):

    get_product.delay(id)

    prod_obj = cache.get('prod_obj' + str(id))
    images = cache.get('images'+str(id))
    prod_features_obj = cache.get('prod_features_obj'+str(id))
    bus_data = cache.get('bus_data' + str(id))

    if not prod_obj and images and prod_features_obj and bus_data:
        prod_obj, prod_photos_obj, prod_features_obj, bus_data = get_product(id)

    context = {
        'bus_data': bus_data,
        'prod_obj': prod_obj,
        'images': images,
        'prod_features_obj': prod_features_obj
    }
    return render(request, 'viewProduct.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def add_product(request, id=0):
    s_list = []
    view_image = None
    prod = None
    prod_photos = None
    prod_features = None

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        staff_obj = Employee.objects.filter(Business=buss)
        for i in staff_obj:
            s_list.append(i.User)

        cat_obj = CatalogueCategories.objects.filter(Business=buss)

        if id != 0:
            try:
                prod = CatalogueProduct.objects.get(pk=id)
                prod_photos = CatalogueProductPhoto.objects.filter(Product__id=prod.id)
                prod_features = CatalogueProductFeature.objects.filter(Product__id=prod.id)
            except CatalogueProduct.DoesNotExist:
                return redirect('/add_product/')

        if request.method == 'POST':
            if 'product' in request.POST:
                product_name = request.POST.get("product_name")
                product_category = request.POST.get("product_category")
                price = request.POST.get("product_price")
                images = request.FILES.getlist("product_images")
                product_description = request.POST.get("product_description")

                catalogue_category = CatalogueCategories.objects.get(Business=buss, pk=int(product_category))

                if not prod:
                    prod = CatalogueProduct(Business=buss, Category=catalogue_category, Name=product_name, Price=price,
                                            Description=product_description)
                    prod.save()
                    if images:
                        for i in images:
                            photo = CatalogueProductPhoto(Business=buss, Product=prod, Photo=i)
                            photo.save()
                    return redirect(f'/add_product/{prod.id}/')
                elif prod:
                    if prod.Name != product_name:
                        prod.Name = product_name
                    if prod.Category != catalogue_category:
                        prod.Category = catalogue_category
                    if prod.Price != price:
                        prod.Price = price
                    if prod.Description != product_description:
                        prod.Description = product_description
                    prod.save()

                    if images:
                        for i in images:
                            photo = CatalogueProductPhoto(Business=buss, Product=prod, Photo=i)
                            photo.save()

                    return redirect(f'/add_product/{prod.id}/')
            if 'add_feature' in request.POST:
                feature_name = request.POST.get("feature_name")
                feature_description = request.POST.get("feature_description")

                CatalogueProductFeature(Business=buss, Product=prod, Name=feature_name, Description=feature_description).save()
                prod_features = CatalogueProductFeature.objects.filter(Product__id=prod.id)

            if 'delete_photo' in request.POST:
                photo_id = request.POST.get('delete_photo')
                photo_id = int(photo_id)
                try:
                    CatalogueProductPhoto.objects.get(pk=photo_id).delete()
                    prod_photos = CatalogueProductPhoto.objects.filter(Product__id=prod.id)
                except Exception as e:
                    messages.error(request, f'{e}')

            if 'delete_feature' in request.POST:
                feature_id = request.POST.get('delete_feature')
                feature_id = int(feature_id)
                try:
                    CatalogueProductFeature.objects.get(pk=feature_id).delete()
                    prod_features = CatalogueProductFeature.objects.filter(Product__id=prod.id)
                except Exception as e:
                    messages.error(request, f'{e}')

            if 'view_image' in request.POST:
                photo_id = request.POST.get('view_image')
                photo_id = int(photo_id)
                try:
                    view_image = CatalogueProductPhoto.objects.get(pk=photo_id)
                except CatalogueProductPhoto.DoesNotExist:
                    messages.error(request, 'failed to process image')

    except Employee.DoesNotExist:
        return HttpResponse('Error *staff does not exist at create post* please contact developer')

    context = {
        'cat_obj': cat_obj,
        's_list': s_list,
        'view_image': view_image,
        'prod': prod,
        'prod_photos': prod_photos,
        'prod_features': prod_features,
    }
    return render(request, 'addProduct.html', context)


def view_buss_type_products(request, business_type=''):
    content = None
    search1 = None
    search2 = None
    lookup_word = None

    bus_types = {
        'School & Office supplies': 'books', 'Furniture': 'chair', 'Home appliances': 'tv',
        'Consumer Electronics': 'devices', 'Food & Beverages': 'liquor', 'Security & Safety': 'lock_open',
        'Cars, spare parts & accessories': 'car_repair', 'Construction': 'roofing', 'Tools & Hardware': 'handyman',
        'Farm equipment & chemicals': 'agriculture', 'Health & Personal Care': 'monitor_heart',
        'Hotel and Lodging': ' hotel', 'Entertainment': 'sports_kabaddi', 'Sports': 'sports_soccer',
        'Real Estate': 'real_estate_agent'
    }
    dict_size = len(bus_types)
    group_size = dict_size // 3

    group1 = dict(list(bus_types.items())[:group_size])
    group2 = dict(list(bus_types.items())[group_size:(group_size * 2)])
    group3 = dict(list(bus_types.items())[(group_size * 2):(group_size * 3)])

    business_type.replace('%', ' ')

    get_content.delay(business_type)
    products = cache.get(business_type)

    if not products:
        products = get_content(business_type)

    pages = Paginator(products, 8)

    if request.method == 'POST':
        if 'lookup_word' in request.POST:
            lookup_word = request.POST.get('lookup_word')
            search1, search2 = query_item_by_letter1(lookup_word)

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'close_search' in request.POST:
            if search1 and search2 or search1 or search2:
                search1 = None
                search2 = None

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'view_type' in request.POST:
            view_type = request.POST.get('view_type')
            view_type.replace(' ', '%')

            return redirect(f'/viewBusinessTypeProducts/{view_type}/')

    if request.method == 'GET':
        page_number = request.GET.get('page')
        content = pages.get_page(page_number)

    context = {
        'content': content,
        'business_type': business_type,
        'search1': search1,
        'search2': search2,
        'lookup_word': lookup_word,
        'group1': group1,
        'group2': group2,
        'group3': group3,
    }
    return render(request, 'viewBusinessTypeProducts.html', context)
