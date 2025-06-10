import random
from django.shortcuts import render, redirect, HttpResponse
from catalogue.models import *
from User.models import Employee, Business, Profile
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models.functions import Random
from User.decorator import allowed_users
from inventory.models import InventoryCategory
from fuzzywuzzy import fuzz
from django.contrib import messages
from django.db.models import Q
from django.core.cache import cache
from celery import shared_task
from django.core import serializers
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout
# Create your views here.


# lookup this product name in this business profile
def query_item_by_letter(lookup_word, buss_id):
    """
    search1 = Products.objects.filter(Q(name__icontains=lookup_word))
    search2 = Categories.objects.filter(Q(name__icontains=lookup_word))
    """
    match1 = []
    match2 = []
    img_li = []
    photo = None
    lookup1 = CatalogueProduct.objects.filter(Business__id=buss_id).order_by('-id')
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


# lookup this product name
def query_item_by_letter1(lookup_word):
    """
    search1 = Products.objects.filter(Q(name__icontains=lookup_word))
    search2 = Categories.objects.filter(Q(name__icontains=lookup_word))
    """
    match1 = []
    match2 = []
    img_li = []
    photo = None
    lookup1 = CatalogueProduct.objects.all().order_by('-id')
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


# lookup this product name in this business type
def query_item_by_letter2(lookup_word, business_type):
    """
    search1 = Products.objects.filter(Q(name__icontains=lookup_word))
    search2 = Categories.objects.filter(Q(name__icontains=lookup_word))
    """
    match1 = []
    match2 = []
    img_li = []
    photo = None
    lookup1 = CatalogueProduct.objects.filter(Business__Type=business_type).order_by('-id')
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
                    content = list(content)[:3]
                categories[i] = []
                for c in content:
                    print(c.Name, c.id)
                    img = CatalogueProductPhoto.objects.filter(Product=c.id)
                    for p in img:
                        images.append(p.Photo.url)
                        random.shuffle(images)
                    example = {'Business_id': c.Business.id, 'Business_Name': c.Business.Name, 'Product_Name': c.Name,
                               'Product_Price': c.Price, 'Product_Photo': images[0]}
                    categories[i].append(example)
                    images = []
    cache.set('categories', categories, 3600)
    return categories


def get_user_profile(user_id):
    try:
        profile = Profile.objects.get(User__id=user_id)
    except Profile.DoesNotExist:
        profile = None

    return profile


def comment_likes_unlikes(user_id, comment_id):
    comment_like_count = LikeComment.objects.filter(Comment__id=comment_id).count()
    if not comment_like_count:
        comment_like_count = 0

    try:
        LikeComment.objects.get(Comment__id=comment_id, User__id=user_id)
        user_liked_comment = True
    except LikeComment.DoesNotExist:
        user_liked_comment = False

    try:
        UnLikeComment.objects.get(Comment__id=comment_id, User__id=user_id)
        user_unliked_comment = True
    except UnLikeComment.DoesNotExist:
        user_unliked_comment = False

    comment_unlike_count = UnLikeComment.objects.filter(Comment__id=comment_id).count()
    if not comment_unlike_count:
        comment_unlike_count = 0

    return user_liked_comment, user_unliked_comment, comment_like_count, comment_unlike_count


def get_likes_and_comments(product_id, user_id):
    product_likes = LikeProduct.objects.filter(Product__id=product_id)
    if product_likes.exists():
        likes = product_likes.count()
    else:
        likes = 0
    if user_id != 0:
        try:
            LikeProduct.objects.get(Product__id=product_id, User=user_id)
            user_liked = True
        except LikeProduct.DoesNotExist:
            user_liked = False
    else:
        user_liked = False

    product_unlikes = UnLikeProduct.objects.filter(Product__id=product_id)
    if product_unlikes.exists():
        unlikes = product_unlikes.count()
    else:
        unlikes = 0
    if user_id != 0:
        try:
            UnLikeProduct.objects.get(Product__id=product_id, User=user_id)
            user_unliked = True
        except UnLikeProduct.DoesNotExist:
            user_unliked = False
    else:
        user_unliked = False

    comments_obj = Comments.objects.filter(Product__id=product_id, Root__isnull=True)
    comments = {}
    comment_count = 0
    if comments_obj.exists():
        comment_count = comments_obj.count()
        for i in comments_obj:
            profile = get_user_profile(i.User.id)
            if not profile.Photo:
                photo = None
            else:
                photo = profile.Photo.url
            user_liked_comment, user_unliked_comment, comment_like_count, comment_unlike_count = comment_likes_unlikes(
                user_id, i.id)
            comments[i.id] = {'user_name': i.User.get_full_name(), 'date': i.Date, 'photo': photo, 'comment': i.Comment,
                              'user_liked_comment': user_liked_comment, 'user_unliked_comment': user_unliked_comment,
                              'comment_like_count': comment_like_count, 'comment_unlike_count': comment_unlike_count,
                              'sub_comments': {}}

            sub_comments = Comments.objects.filter(Product__id=product_id, Root__id=i.id)
            if sub_comments.exists():
                for s in sub_comments:
                    profile_ = get_user_profile(s.User.id)
                    if not profile_.Photo:
                        photo_ = None
                    else:
                        photo_ = profile_.Photo.url
                    user_liked_comment, user_unliked_comment, comment_like_count, comment_unlike_count = (
                        comment_likes_unlikes(user_id, s.id))
                    comments[i.id]['sub_comments'][s.id] = {'user_name': s.User.get_full_name(), 'date': s.Date,
                                                            'photo': photo_, 'comment': s.Comment,
                                                            'user_liked_comment': user_liked_comment,
                                                            'user_unliked_comment': user_unliked_comment,
                                                            'comment_like_count': comment_like_count,
                                                            'comment_unlike_count': comment_unlike_count}
                sub_comments_count = sub_comments.count()
            else:
                sub_comments_count = 0

            comments[i.id]['sub_comments_count'] = sub_comments_count
            comment_count += sub_comments_count
    return likes, user_liked, unlikes, user_unliked, comment_count, comments


@shared_task()
def get_content(buss_type='', user_id=0):
    content = []

    if buss_type != '':
        prod_obj = CatalogueProduct.objects.filter(Business__Type=buss_type).order_by('id')
    else:
        prod_obj = CatalogueProduct.objects.all().order_by('id')

    for i in prod_obj:
        # product pictures
        picture_li = []
        photos = CatalogueProductPhoto.objects.filter(Product=i.id)
        if photos:
            for p in photos:
                picture_li.append(p.Photo.url)

        # get likes and comments
        likes, user_liked, unlikes, user_unliked, comment_count, comments = get_likes_and_comments(i.id, user_id)

        new_entry = {'store_name': i.Business.Name, 'store_photo': i.Business.Photo.url, 'product_id': i.id,
                     'product_name': i.Name, 'product_price': i.Price, 'product_photo': picture_li[0],
                     'product_description': i.Description, 'likes': likes, 'user_liked': user_liked, 'unlikes': unlikes,
                     'user_unliked': user_unliked, 'comment_count': comment_count, 'comments': comments}

        content.append(new_entry)

    if buss_type == '':
        cache.set('content', content, 300)
    else:
        cache.set(buss_type, content, 300)

    return content


@shared_task()
def get_product(p_id, user_id=0):
    business = {}
    product = {}

    try:
        prod = CatalogueProduct.objects.get(pk=p_id)
        prod_photos_obj = CatalogueProductPhoto.objects.filter(Product=prod.id)
        feat = CatalogueProductFeature.objects.filter(Product=prod.id)
        buss = Business.objects.get(pk=prod.Business.id)

        # get likes and comments
        likes, user_liked, unlikes, user_unliked, comment_count, comments = get_likes_and_comments(p_id, user_id)

        product = {'id': prod.id, 'Category': prod.Category.id, 'Name': prod.Name, 'Price': prod.Price,
                   'Description': prod.Description, 'likes': likes, 'user_liked': user_liked, 'unlikes': unlikes,
                   'user_unliked': user_unliked, 'comment_count': comment_count,  'comments': comments}

        images = []
        for i in prod_photos_obj:
            images.append(i.Photo.url)

        features = {}
        for f in feat:
            features[f.id] = {'Name': f.Name, 'Description': f.Description}
        product['images'] = images
        product['features'] = features

        linkedin = buss.Linkedin.replace("http://", "")
        linkedin = linkedin.replace("https://", "")
        facebook = buss.Facebook.replace("http://", "")
        facebook = facebook.replace("https://", "")
        instagram = buss.Instagram.replace("http://", "")
        instagram = instagram.replace("https://", "")

        business = {'id': buss.id, 'Name': buss.Name, 'Email': buss.Email, 'Contact1': buss.Contact1,
                    'Contact2': buss.Contact2, 'Instagram': instagram, 'Facebook': facebook, 'Linkedin': linkedin}

        cache.set('product'+str(p_id), product, 3600)
        cache.set('business'+str(p_id), business, 3600)

        return business, product
    except CatalogueProduct.DoesNotExist:
        return business, product


def catalogue_login(request):
    name = request.POST.get('username')
    password = request.POST.get('password')

    user = authenticate(request, username=name, password=password)

    return user


def market_view(request):
    content = None
    search1 = None
    search2 = None
    lookup_word = None
    user_ = None

    if request.user.is_anonymous:
        registration_form = True
    else:
        registration_form = False
        try:
            user_ = User.objects.get(pk=request.user.id)
            try:
                employee = Employee.objects.get(User__id=user_.id)
                if employee.AccessLevel.id == 1:
                    allowed = True
                elif employee.AccessLevel == 2:
                    allowed = True
            except Employee.DoesNotExist:
                pass
        except User.DoesNotExist:
            pass

    bus_types = {
        'Groceries': 'shopping_basket', 'School & Office supplies': 'library_books', 'Furniture': 'chair',
        'Home appliances': 'tv',
        'Consumer Electronics': 'devices', 'Food & Beverages': 'liquor', 'Security & Safety': 'lock_open',
        'Cars, spare parts & accessories': 'car_repair', 'Construction': 'roofing', 'Tools & Hardware': 'handyman',
        'Farm equipment & chemicals': 'agriculture', 'Health & Personal Care': 'monitor_heart',
        'Hotel and Lodging': ' hotel', 'Entertainment': 'sports_kabaddi', 'Sports': 'sports_soccer',
        'Real Estate': 'real_estate_agent', 'Fashion(Apparel, shoes, Jewerly)': 'checkroom', 'Cosmetics': 'spa'
    }
    dict_size = len(bus_types)
    group_size = dict_size // 3

    group1 = dict(list(bus_types.items())[:group_size])
    group2 = dict(list(bus_types.items())[group_size:(group_size * 2)])
    group3 = dict(list(bus_types.items())[(group_size * 2):])

    products_in_categories.delay()
    categories = cache.get('categories')
    if not categories:
        categories = products_in_categories()

    if user_:
        get_content.delay('', user_.id)
    else:
        get_content.delay('', 0)
    data = cache.get('content')
    if not data:
        if user_:
            data = get_content('', user_.id)
        else:
            data = get_content('', 0)

    pages = Paginator(data, 30)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if 'like' in request.POST:
            return JsonResponse({"message", "liked"})
        elif 'comment' in request.POST:
            return JsonResponse({"message", "commented"})
    if request.method == 'POST':
        lookup_word = request.POST.get('lookup_word')
        if lookup_word:
            search1, search2 = query_item_by_letter1(lookup_word)

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'login' in request.POST:
            user_obj = catalogue_login(request)
            if not user_obj:
                messages.error(request, 'Enter a valid username and password!')
            else:
                login(request, user_obj)
                return redirect('/market/')

        if 'close_search' in request.POST:
            if search1 and search2 or search1 or search2:
                search1 = None
                search2 = None

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'view_type' in request.POST:
            view_type = request.POST.get('view_type')
            view_type.replace(' ', '%')

            return redirect(f'/marketSection/{view_type}/')

        if 'goto' in request.POST:
            goto = request.POST.get('goto')

            goto = goto.replace(' ', '%')
            return redirect(f'/catalogue/{goto}/')

        if 'signup' in request.POST:
            result = catalogue_signup(request)

            if result == 'user already exists':
                messages.error(request, 'user already exists')
            if result == 'success':
                messages.info(request, "Would you like to set up your own Business Catalogue")
            if result == 'passwords dont match':
                messages.error(request, 'passwords do not match')

        if "yes" in request.POST:
            return redirect('/edit_business_profile')

        if "no" in request.POST:
            # gets all messages for the current request session and consumes them; messages are
            # stored in sessions until they're viewed
            list(messages.get_messages(request))

    if request.method == 'GET':
        page_number = request.GET.get('page')
        content = pages.get_page(page_number)

    context = {
        'content': content,
        'search1': search1,
        'search2': search2,
        'lookup_word': lookup_word,
        'billboard': categories,
        'group1': group1,
        'group2': group2,
        'group3': group3,
        'registration_form': registration_form
    }
    return render(request, 'market.html', context)


def view_buss_type_products(request, business_type=''):
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

    business_type.replace('%', ' ')

    get_content.delay(business_type)
    products = cache.get(business_type)

    if not products:
        products = get_content(business_type)

    pages = Paginator(products, 30)

    if request.method == 'POST':
        lookup_word = request.POST.get('lookup_word')
        if lookup_word:
            search1, search2 = query_item_by_letter2(lookup_word, business_type)

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'login' in request.POST:
            user_obj = catalogue_login(request)
            if not user_obj:
                messages.error(request, 'Enter a valid username and password!')
            else:
                login(request, user_obj)
                return redirect('/market/')

        if 'close_search' in request.POST:
            if search1 and search2 or search1 or search2:
                search1 = None
                search2 = None

            page_number = request.GET.get('page')
            content = pages.get_page(page_number)

        if 'view_type' in request.POST:
            view_type = request.POST.get('view_type')
            view_type.replace(' ', '%')

            return redirect(f'/marketSection/{view_type}/')

    if request.method == 'GET':
        page_number = request.GET.get('page')
        content = pages.get_page(page_number)

    context = {
        'content': content,
        'client': client,
        'business_type': business_type,
        'search1': search1,
        'search2': search2,
        'lookup_word': lookup_word,
        'group1': group1,
        'group2': group2,
        'group3': group3,
    }
    return render(request, 'catalogue/viewBusinessTypeProducts.html', context)


@shared_task()
def get_catalogue_content(buss_id):
    content = {}
    cat_obj = CatalogueCategories.objects.filter(Business__id=buss_id)
    for c in cat_obj:
        product_count = CatalogueProduct.objects.filter(Category=c).count()

        content[c.id] = {'Name': c.Name, 'Photo': c.Photo.url, 'Count': product_count}

    cache.set(f'catalogue'+str(buss_id), content, 3600)
    return content


def catalogue_view(request, store_name=''):
    s_list = []
    categories = {}
    cat_obj = None
    buss = None
    prod_obj = None
    prod_photos_obj = None
    search1 = None
    search2 = None

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        staff_obj = Employee.objects.filter(Business=buss)
        for i in staff_obj:
            s_list.append(i.User)
    except Employee.DoesNotExist:
        if store_name != '':
            store_name = store_name.replace('%', ' ')
            try:
                buss = Business.objects.get(Name=store_name)
            except Business.DoesNotExist:
                return redirect(request.META.get('HTTP_REFERER'))

        else:
            return redirect('/login/')

    goto_business = buss.Name
    goto_business = goto_business.replace(' ', '%')

    get_catalogue_content.delay(buss.id)
    content = cache.get(f'catalogue' + str(buss.id))
    if not content:
        content = get_catalogue_content(buss.id)

    if request.method == 'POST':
        lookup_word = request.POST.get('lookup_word')
        if lookup_word:
            search1, search2 = query_item_by_letter(lookup_word, buss.id)

    context = {
        's_list': s_list,
        'bus_data': buss,
        'goto_business': goto_business,
        'content': content,
        'search1': search1,
        'search2': search2,
    }
    return render(request, 'catalogue/catalogue.html', context)


@shared_task()
def get_category_product(category_id):
    products = []
    prod_obj = CatalogueProduct.objects.filter(Category__id=category_id)

    for i in prod_obj:
        product_image = []
        prod_photos_obj = CatalogueProductPhoto.objects.filter(Product__id=i.id)
        for x in prod_photos_obj:
            if x.Product == i:
                product_image.append(x.Photo.url)

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
    return render(request, 'catalogue/addCategory.html', context)


def category(request, id=0):
    try:
        cat_obj = CatalogueCategories.objects.get(pk=id)

        bus_data = Business.objects.filter(pk=cat_obj.Business.id)

        try:
            employee = Employee.objects.get(Business__id=bus_data[0].id, User=request.user.id)
        except Employee.DoesNotExist:
            employee = None

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
        'employee': employee
    }
    return render(request, 'catalogue/category.html', context)


def catalogue_signup(request):
    username = request.POST.get('username')
    firstname = request.POST.get('first name')
    lastname = request.POST.get('last name')
    email = request.POST.get('email')
    password1 = request.POST.get('password1')
    password2 = request.POST.get('password2')

    if password1 == password2:
        try:
            u = User.objects.get(username=username)
            return 'user already exists'
        except User.DoesNotExist:
            new_user = User.objects.create_user(username=username, first_name=firstname, last_name=lastname,
                                                email=email, password=password2)
            new_user.save()

            new_profile = Profile(User=new_user)
            new_profile.save()

            user = authenticate(request, username=username, password=password2)
            login(request, user)

            # messages.info(request, "Would you like to set up your own Business Catalogue")
            return 'success'
    else:
        # messages.error(request, 'passwords do not match')
        return 'password do not match'


def view_product(request, id=0):
    allowed = False
    reply_to_comment = None
    user_id = 0
    back_url = None
    if request.user.is_anonymous:
        registration_form = True
    else:
        registration_form = False
        try:
            user_id = User.objects.get(pk=request.user.id).id
            try:
                employee = Employee.objects.get(User__id=user_id)
                if employee.AccessLevel.id == 1:
                    allowed = True
                elif employee.AccessLevel == 2:
                    allowed = True
            except Employee.DoesNotExist:
                pass
        except User.DoesNotExist:
            pass

        back_url = cache.get(f"{request.user.id}-{id}-edit_product_income_transaction_http_referer")
        if not back_url:
            cache.set(f"{request.user.id}-{id}-edit_product_income_transaction_http_referer",
                      request.META.get("HTTP_REFERER"), 300)
            back_url = cache.get(f"{request.user.id}-{id}-edit_product_income_transaction_http_referer")

    get_product.delay(id, user_id)
    product = cache.get('product' + str(id))
    business = cache.get('business' + str(id))

    if product is None:
        product, business = get_product(id, user_id)
        return redirect(f'/viewProduct/{id}/')

    if request.method == 'POST':
        if 'login' in request.POST:
            user_obj = catalogue_login(request)
            if not user_obj:
                messages.error(request, 'Enter a valid username and password!')
            else:
                login(request, user_obj)
                return redirect(f'/viewProduct/{id}/')

        if 'edit' in request.POST:
            return redirect(f"/editProduct/{product['id']}/")

        if 'delete' in request.POST:
            messages.warning(request, 'do you really want to delete this product')

        if 'confirm' in request.POST:
            try:
                CatalogueProduct.objects.get(pk=product['id']).delete()
                cache.delete('product' + str(id))
                product = cache.get('product' + str(id))
                if product is None:
                    return redirect(request.META.get('HTTP_REFERER'))
                else:
                    messages.error(request, f'failed to delete product')
            except Exception as e:
                messages.error(request, f'failed to delete product; {e}')

        if "un-confirm" in request.POST:
            list(messages.get_messages(request))

        if 'like' in request.POST:
            try:
                LikeProduct.objects.get(User__id=request.user.id).delete()
            except LikeProduct.DoesNotExist:
                try:
                    try:
                        UnLikeProduct.objects.get(User__id=request.user.id).delete()
                    except UnLikeProduct.DoesNotExist:
                        pass
                    LikeProduct(Product=CatalogueProduct.objects.get(pk=id), User=request.user).save()
                except Exception as e:
                    messages.error(request, f'{e}')

            product, business = get_product(id, user_id)
            return redirect(f'/viewProduct/{id}/')

        if 'unlike' in request.POST:
            try:
                UnLikeProduct.objects.get(User__id=request.user.id).delete()
            except UnLikeProduct.DoesNotExist:
                try:
                    try:
                        LikeProduct.objects.get(User__id=request.user.id).delete()
                    except LikeProduct.DoesNotExist:
                        pass
                    UnLikeProduct(Product=CatalogueProduct.objects.get(pk=id), User=request.user).save()
                except Exception as e:
                    messages.error(request, f'{e}')

            product, business = get_product(id, user_id)
            return redirect(f'/viewProduct/{id}/')

        if 'add comment' in request.POST:
            comment_id = request.POST.get("add comment")
            new_comment = request.POST.get("new comment")

            try:
                if comment_id:
                    record_comment = Comments(Product=CatalogueProduct.objects.get(pk=id), User=request.user,
                                              Root=Comments.objects.get(pk=int(comment_id)), Comment=new_comment)
                    record_comment.save()
                    messages.success(request, "delivered")
                else:
                    record_comment = Comments(Product=CatalogueProduct.objects.get(pk=id), User=request.user,
                                              Comment=new_comment)
                    record_comment.save()
                    messages.success(request, "delivered")
            except Exception as e:
                messages.error(request, f'{e}')

            product, business = get_product(id, user_id)
            return redirect(f'/viewProduct/{id}/')

        if "like comment" in request.POST:
            comment_id = request.POST.get("like comment")

            try:
                LikeComment.objects.get(Comment__id=Comments.objects.get(pk=int(comment_id)).id,
                                        User=request.user).delete()
            except LikeComment.DoesNotExist:
                try:
                    try:
                        UnLikeComment.objects.get(Comment__id=Comments.objects.get(pk=int(comment_id)).id,
                                                  User=request.user).delete()
                    except UnLikeComment.DoesNotExist:
                        pass
                    LikeComment(Comment=Comments.objects.get(pk=int(comment_id)), User=request.user).save()
                except Exception as e:
                    messages.error(request, f'{e}')

            product, business = get_product(id, user_id)
            return redirect(f'/viewProduct/{id}/')

        if "unlike comment" in request.POST:
            comment_id = request.POST.get("unlike comment")
            try:
                UnLikeComment.objects.get(Comment__id=Comments.objects.get(pk=int(comment_id)).id,
                                          User=request.user).delete()
            except UnLikeComment.DoesNotExist:
                try:
                    try:
                        LikeComment.objects.get(Comment__id=Comments.objects.get(pk=int(comment_id)).id,
                                                User=request.user).delete()
                    except LikeComment.DoesNotExist:
                        pass
                    UnLikeComment(Comment=Comments.objects.get(pk=int(comment_id)), User=request.user).save()
                except Exception as e:
                    messages.error(request, f'{e}')

            product, business = get_product(id, user_id)
            return redirect(f'/viewProduct/{id}/')

        if "reply comment" in request.POST:
            root_id = request.POST.get("root_id")
            new_comment = request.POST.get("new_comment")
            try:
                root = Comments.objects.get(pk=int(root_id), Root_isnull=True)

                Comments(Product=root.Product, User=request.user, Root=root, Comment=new_comment).save()
            except Exception as e:
                messages.error(request, f"{e}")

        if "delete comment" in request.POST:
            comment_id = request.POST.get("delete comment")

            try:
                Comments.objects.get(pk=int(comment_id)).delete()
            except Comments.DoesNotExist:
                messages.error(request, f'failed to delete the comment')

            product, business = get_product(id, user_id)
            return redirect(f'/viewProduct/{id}/')

        if 'signup' in request.POST:
            result = catalogue_signup(request)

            if result == 'user already exists':
                messages.error(request, 'user already exists')
            if result == 'success':
                messages.info(request, "Would you like to set up your own Business Catalogue")
            if result == 'passwords dont match':
                messages.error(request, 'passwords do not match')

        if "yes" in request.POST:
            return redirect('/edit_business_profile')

        if "no" in request.POST:
            # gets all messages for the current request session and consumes them; messages are
            # stored in sessions until they're viewed
            list(messages.get_messages(request))

    context = {
        'bus_data': business,
        'product': product,
        'allowed': allowed,
        'registration_form': registration_form,
        "reply_to_comment": reply_to_comment,
        'back_url': back_url
    }
    return render(request, 'catalogue/viewProduct.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def add_product(request):
    s_list = []
    view_image = None
    product = None
    prod_photos = None
    prod_features = None

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        staff_obj = Employee.objects.filter(Business=buss)
        for i in staff_obj:
            s_list.append(i.User)

        cat_obj = CatalogueCategories.objects.filter(Business=buss)

        if request.method == 'POST':
            if 'product' in request.POST:
                product_name = request.POST.get("product_name")
                product_category = request.POST.get("product_category")
                price = request.POST.get("product_price")
                images = request.FILES.getlist("product_images")
                product_description = request.POST.get("product_description")

                catalogue_category = CatalogueCategories.objects.get(Business=buss, pk=int(product_category))

                product = CatalogueProduct(Business=buss, Category=catalogue_category, Name=product_name, Price=price,
                                        Description=product_description)
                product.save()

                if len(images) > 10:
                    images = images[0:9]
                if images:
                    for i in images:
                        photo = CatalogueProductPhoto(Business=buss, Product=product, Photo=i)
                        photo.save()
                return redirect(f'/editProduct/{product.id}/')

    except Employee.DoesNotExist:
        return HttpResponse('Error *staff does not exist at create post* please contact developer')

    context = {
        'cat_obj': cat_obj,
        's_list': s_list,
        'view_image': view_image,
        'prod': product,
        'prod_photos': prod_photos,
        'prod_features': prod_features,
    }
    return render(request, 'catalogue/addCatalogueProduct.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def edit_product(request, id=0):
    s_list = []
    view_image = None
    product = None
    product_photos = None
    product_features = None

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        staff_obj = Employee.objects.filter(Business=buss)
        for i in staff_obj:
            s_list.append(i.User)

        cat_obj = CatalogueCategories.objects.filter(Business=buss)

        try:
            product = CatalogueProduct.objects.get(pk=id)
            product_photos = CatalogueProductPhoto.objects.filter(Product__id=product.id)
            product_features = CatalogueProductFeature.objects.filter(Product__id=product.id)
        except CatalogueProduct.DoesNotExist:
            return redirect(request.META.get('HTTP_REFERER'))

        if request.method == 'POST':
            if 'product' in request.POST:
                product_name = request.POST.get("product_name")
                product_category = request.POST.get("product_category")
                price = request.POST.get("product_price")
                images = request.FILES.getlist("product_images")
                product_description = request.POST.get("product_description")

                catalogue_category = CatalogueCategories.objects.get(Business=buss, pk=int(product_category))

                if product.Name != product_name:
                    product.Name = product_name
                if product.Category != catalogue_category:
                    product.Category = catalogue_category
                if product.Price != price:
                    product.Price = price
                if product.Description != product_description:
                    product.Description = product_description
                product.save()

                if images:
                    for i in images:
                        photo = CatalogueProductPhoto(Business=buss, Product=product, Photo=i)
                        photo.save()

                return redirect(f'/editProduct/{product.id}/')
            if 'add_feature' in request.POST:
                feature_name = request.POST.get("feature_name")
                feature_description = request.POST.get("feature_description")

                CatalogueProductFeature(Business=buss, Product=product, Name=feature_name, Description=feature_description).save()
                product_features = CatalogueProductFeature.objects.filter(Product__id=product.id)

            if 'delete_photo' in request.POST:
                photo_id = request.POST.get('delete_photo')
                photo_id = int(photo_id)
                try:
                    CatalogueProductPhoto.objects.get(pk=photo_id).delete()
                    product_photos = CatalogueProductPhoto.objects.filter(Product__id=product.id)
                except Exception as e:
                    messages.error(request, f'{e}')

            if 'delete_feature' in request.POST:
                feature_id = request.POST.get('delete_feature')
                feature_id = int(feature_id)
                try:
                    CatalogueProductFeature.objects.get(pk=feature_id).delete()
                    product_features = CatalogueProductFeature.objects.filter(Product__id=product.id)
                except Exception as e:
                    messages.error(request, f'{e}')

            if 'view_image' in request.POST:
                photo_id = request.POST.get('view_image')
                photo_id = int(photo_id)
                try:
                    view_image = CatalogueProductPhoto.objects.get(pk=photo_id)
                except CatalogueProductPhoto.DoesNotExist:
                    messages.error(request, 'failed to process image')

            if 'close' in request.POST:
                view_image = None

    except Employee.DoesNotExist:
        return HttpResponse('Error *staff does not exist at create post* please contact developer')

    context = {
        'cat_obj': cat_obj,
        's_list': s_list,
        'view_image': view_image,
        'product': product,
        'product_photos': product_photos,
        'product_features': product_features,
    }
    return render(request, 'catalogue/editCatalogueProduct.html', context)

