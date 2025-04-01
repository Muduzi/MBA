from django.shortcuts import render, redirect, HttpResponse
from .models import ProductIncome, ProductGeneralContent
from datetime import datetime, timedelta
from calendar import monthrange
from inventory.models import InventoryCategory, InventoryProduct, InventoryProductInfo
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
from statements.ProfitAndLoss import get_tax_year
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from celery import shared_task


@shared_task()
def product_income_per_group_this_month(buss):
    date = datetime.now()
    categories = {}
    products = {}
    date_range = monthrange(date.year, date.month)
    start = datetime(date.year, date.month, 1)
    end = datetime(date.year, date.month, date_range[1])

    total = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    grand_total = total.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    """"Income per Inventory Category"""
    cat_obj = InventoryCategory.objects.filter(Business__id=buss)
    for c in cat_obj:
        income = ProductIncome.objects.filter(Q(Business__id=buss), Q(Product__Category=c), Q(Date__range=(start, end)))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        try:
            percentage = round((amount / grand_total) * 100)
        except ZeroDivisionError:
            percentage = 0
        categories[c] = {}
        categories[c]['Quantity'] = quantity
        categories[c]['Percentage'] = percentage
        categories[c]['Amount'] = amount
    categories = dict(sorted(categories.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"Income per service"""
    prod_obj = InventoryProduct.objects.filter(Business__id=buss)
    for p in prod_obj:
        income = ProductIncome.objects.filter(Business__id=buss, Product=p, Date__range=(start, end))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        try:
            percentage = round((amount/grand_total)*100)
        except ZeroDivisionError:
            percentage = 0
        products[p.id] = {}
        products[p.id]['Name'] = p.Name
        products[p.id]['Brand'] = p.Brand
        products[p.id]['Size'] = p.Size
        products[p.id]['Quantity'] = quantity
        products[p.id]['Percentage'] = percentage
        products[p.id]['Amount'] = amount
    products = dict(sorted(products.items(), key=lambda item: item[1]['Amount'], reverse=True))

    cache.set(str(buss)+'categories_m', categories, 300)
    cache.set(str(buss)+'products_m', products, 300)

    return categories, products


@shared_task()
def product_daily_records_this_month(buss):
    date = datetime.now()
    income_this_month = {}
    date_range = monthrange(date.year, date.month)
    start = datetime(date.year, date.month, 1)
    end = datetime(date.year, date.month, date_range[1])

    for i in range(1, date_range[1]):
        check_date = datetime(date.year, date.month, i)
        data = ProductIncome.objects.filter(Business__id=buss, Date__date=check_date)
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        data = ProductIncome.objects.filter(Business__id=buss, PMode='Cash', Date__date=check_date)
        cash = data.aggregate(Sum('Amount'))
        cash = cash['Amount__sum']
        if not cash:
            cash = 0

        data = ProductIncome.objects.filter(Business__id=buss, PMode='Credit', Date__date=check_date)
        credit = data.aggregate(Sum('Amount'))
        credit = credit['Amount__sum']
        if not credit:
            credit = 0

        income_this_month[i] = {}
        income_this_month[i]['Amount'] = amount
        income_this_month[i]['Cash'] = cash
        income_this_month[i]['Credit'] = credit

    grand_total = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = grand_total.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    cash_total = ProductIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
    cash = cash_total.aggregate(Sum('Amount'))
    cash = cash['Amount__sum']
    if not cash:
        cash = 0

    credit_total = ProductIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
    credit = credit_total.aggregate(Sum('Amount'))
    credit = credit['Amount__sum']
    if not credit:
        credit = 0

    cache.set(str(buss) + 'total_m', total, 300)
    cache.set(str(buss) + 'cash_m', cash, 300)
    cache.set(str(buss) + 'credit_m', credit, 300)
    cache.set(str(buss) + 'income_this_month', income_this_month, 300)

    return total, cash, credit, income_this_month


@shared_task()
def product_income_per_group_this_year(buss):
    date = datetime.now()
    categories = {}
    products = {}

    this_tax_year = get_tax_year(buss)
    start = this_tax_year.TaxYearStart
    end = this_tax_year.TaxYearEnd

    total = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    grand_total = total.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    """"Income per Inventory Category"""
    cat_obj = InventoryCategory.objects.filter(Business__id=buss)
    for c in cat_obj:
        income = ProductIncome.objects.filter(Q(Business__id=buss), Q(Product__Category=c), Q(Date__range=(start, end)))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        try:
            percentage = round((amount / grand_total) * 100)
        except ZeroDivisionError:
            percentage = 0
        categories[c] = {}
        categories[c]['Quantity'] = quantity
        categories[c]['Percentage'] = percentage
        categories[c]['Amount'] = amount
    categories = dict(sorted(categories.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"Income per products"""
    prod_obj = InventoryProduct.objects.filter(Business__id=buss)
    for p in prod_obj:
        income = ProductIncome.objects.filter(Business__id=buss, Product=p, Date__range=(start, end))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        try:
            percentage = round((amount / grand_total) * 100)
        except ZeroDivisionError:
            percentage = 0
        products[p.id] = {}
        products[p.id]['Name'] = p.Name
        products[p.id]['Brand'] = p.Brand
        products[p.id]['Size'] = p.Size
        products[p.id]['Quantity'] = quantity
        products[p.id]['Percentage'] = percentage
        products[p.id]['Amount'] = amount
    products = dict(sorted(products.items(), key=lambda item: item[1]['Amount'], reverse=True))

    cache.set(str(buss) + 'categories_y', categories, 300)
    cache.set(str(buss) + 'products_y', products, 300)

    return categories, products


@shared_task()
def product_monthly_records_this_year(buss):
    date = datetime.now()
    product_income_this_year = {}

    this_tax_year = get_tax_year(buss)
    start_ = this_tax_year.TaxYearStart
    end_ = this_tax_year.TaxYearEnd

    start = start_.date()
    for month in range(0, 12):
        if start.month == 12:
            end = datetime(start.year+1, 1, start.day)
        else:
            end = datetime(start.year, start.month+1, start.day)

        data = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        data = ProductIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
        cash = data.aggregate(Sum('Amount'))
        cash = cash['Amount__sum']
        if not cash:
            cash = 0

        data = ProductIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
        credit = data.aggregate(Sum('Amount'))
        credit = credit['Amount__sum']
        if not credit:
            credit = 0

        product_income_this_year[start.month] = {}
        product_income_this_year[start.month]['Amount'] = amount
        product_income_this_year[start.month]['Cash'] = cash
        product_income_this_year[start.month]['Credit'] = credit

        if start.month == 12:
            start = datetime(start.year+1, 1, start.day)
        elif start.month < 12:
            start = datetime(start.year, start.month + 1, start.day)

    date_range = monthrange(datetime.now().year, 12)
    start = datetime(date.year, 1, 1)
    end = datetime(date.year, 12, date_range[1])
    grand_total = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = grand_total.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    cash_total = ProductIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
    cash = cash_total.aggregate(Sum('Amount'))
    cash = cash['Amount__sum']
    if not cash:
        cash = 0

    credit_total = ProductIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
    credit = credit_total.aggregate(Sum('Amount'))
    credit = credit['Amount__sum']
    if not credit:
        credit = 0

    cache.set(str(buss) + 'total_y', total, 300)
    cache.set(str(buss) + 'cash_y', cash, 300)
    cache.set(str(buss) + 'credit_y', credit, 300)
    cache.set(str(buss) + 'product_income_this_year', product_income_this_year, 300)

    return total, cash, credit, product_income_this_year


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def product_income_dash(request):
    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business.id

        try:
            general_content = ProductGeneralContent.objects.get(Business=check.Business, Cashier=user_object)
        except ProductGeneralContent.DoesNotExist:
            general_content = None

        product_daily_records_this_month.delay(buss)
        total_m = cache.get(str(buss) + 'total_m')
        cash_m = cache.get(str(buss) + 'cash_m')
        credit_m = cache.get(str(buss) + 'credit_m')
        income_this_month = cache.get(str(buss) + 'income_this_month')

        if not total_m and cash_m and credit_m and income_this_month:
            total_m, cash_m, credit_m, income_this_month = product_daily_records_this_month(buss)

        product_income_per_group_this_month.delay(buss)
        categories_m = cache.get(str(buss)+'categories_m')
        products_m = cache.get(str(buss)+'products_m')

        if not categories_m and products_m:
            categories_m, products_m = product_income_per_group_this_month(buss)

        product_monthly_records_this_year.delay(buss)
        total_y = cache.get(str(buss) + 'total_y')
        cash_y = cache.get(str(buss) + 'cash_y')
        credit_y = cache.get(str(buss) + 'credit_y')
        income_this_year = cache.get(str(buss) + 'income_this_year')

        if not total_y and cash_y and credit_y and income_this_year:
            total_y, cash_y, credit_y, income_this_year = product_monthly_records_this_year(buss)

        product_income_per_group_this_year.delay(buss)
        categories_y = cache.get(str(buss) + 'categories_y')
        products_y = cache.get(str(buss) + 'products_y')

        if not categories_y and products_y:
            categories_y, products_y = product_income_per_group_this_year(buss)

        if request.method == 'POST':
            if 'general_content' in request.POST:
                content = request.POST.get('content')

                if not general_content:
                    general_content = ProductGeneralContent(Business=check.Business, Cashier=user_object, Choice=content).save()
                else:
                    general_content.Choice = content
                    general_content.save()

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'general_content': general_content,

        'total_m': total_m,
        'cash_m': cash_m,
        'credit_m': credit_m,
        'income_m': income_this_month,
        'categories_m': categories_m,
        'products_m': products_m,

        'total_y': total_y,
        'cash_y': cash_y,
        'credit_y': credit_y,
        'income_y': income_this_year,
        'categories_y': categories_y,
        'products_y': products_y,
    }
    return render(request, 'productIncomeDash.html', context)
