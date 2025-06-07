from django.shortcuts import render, HttpResponse
from _datetime import datetime, timezone
from calendar import monthrange
from inventory.models import InventoryCategory, InventoryProduct
from income.models import ProductIncome
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from User.models import Employee
from django.contrib import messages
from celery import shared_task
from income.service_income_history import get_tax_years
from django.core.cache import cache
from .invoice import date_initial


def product_income_per_group_history(buss, start, end):
    categories = {}
    products = {}

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
        categories[c] = {'Quantity': quantity, 'Percentage': percentage, 'Amount': amount}
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
        products[p.id] = {'Name': p.Name, 'Brand': p.Brand, 'Size': p.Size, 'Quantity': quantity,
                          'Percentage': percentage, 'Amount': amount}
    products = dict(sorted(products.items(), key=lambda item: item[1]['Amount'], reverse=True))

    return categories, products


def product_income_daily_history(buss, year_month):
    income_totals_this_month = {}
    date_range = monthrange(year_month.year, year_month.month)
    start = datetime(year_month.year, year_month.month, 1)
    end = datetime(year_month.year, year_month.month, date_range[1])

    for i in range(1, date_range[1]):
        check_date = datetime(year_month.year, year_month.month, i)
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

        income_totals_this_month[i] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    all_transactions = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = all_transactions.aggregate(Sum('Amount'))
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

    return total, cash, credit, income_totals_this_month, all_transactions


def product_income_annual_history(buss, start, end):
    income_year_range = {}

    tax_years, start_, end_ = get_tax_years(buss, start, end)
    for ty in tax_years:
        start_ = ty.TaxYearStart
        end_ = ty.TaxYearEnd

        data = ProductIncome.objects.filter(Business__id=buss, Date__range=(start_, end_))
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        data = ProductIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start_, end_))
        cash = data.aggregate(Sum('Amount'))
        cash = cash['Amount__sum']
        if not cash:
            cash = 0

        data = ProductIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start_, end_))
        credit = data.aggregate(Sum('Amount'))
        credit = credit['Amount__sum']
        if not credit:
            credit = 0

        income_year_range[start_.date()] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    all_transactions = ProductIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = all_transactions.aggregate(Sum('Amount'))
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

    return total, cash, credit, income_year_range, all_transactions


def product_income_history(request):
    total = 0
    cash = 0
    credit = 0
    categories = {}
    products = {}
    income_record = {}
    all_transactions = {}
    start_initial = None
    end_initial = None

    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business.id

        start = cache.get(f'{buss}_{user_object.id}_product_income_history_start')
        end = cache.get(f'{buss}_{user_object.id}_product_income_history_end')

        if start and end:
            difference = abs((start - end)).days

            if difference <= 31:
                total, cash, credit, income_record, all_transactions = product_income_daily_history(buss, start)
                categories, products = product_income_per_group_history(buss, start, end)

            elif difference > 31:
                total, cash, credit, income_record, all_transactions = product_income_annual_history(buss, start, end)

                tax_years, start_, end_ = get_tax_years(buss, start, end)
                categories, products = product_income_per_group_history(buss, start_, end_)

            start_initial = date_initial(start)
            end_initial = date_initial(end)

        if 'filter' in request.POST:
            start = request.POST.get('start')
            end = request.POST.get('end')
            # converting html date input into datetime object

            date_format = '%Y-%m-%d'
            start = datetime.strptime(start, date_format).replace(tzinfo=timezone.utc)
            end = datetime.strptime(end, date_format).replace(tzinfo=timezone.utc)

            cache.set(f'{buss}_{user_object.id}_product_income_history_start', start, 300)
            cache.set(f'{buss}_{user_object.id}_product_income_history_end', end, 300)

            difference = abs((start - end)).days

            if difference <= 31:
                total, cash, credit, income_record, all_transactions = product_income_daily_history(buss, start)
                categories, products = product_income_per_group_history(buss, start, end)

            elif difference > 31:
                total, cash, credit, income_record, all_transactions = product_income_annual_history(buss, start, end)

                tax_years, start_, end_ = get_tax_years(buss, start, end)
                categories, products = product_income_per_group_history(buss, start_, end_)

            start_initial = date_initial(start)
            end_initial = date_initial(end)

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")

    context = {
        'total': total,
        'cash': cash,
        'credit': credit,
        'categories': categories,
        'products': products,
        'income_record': income_record,
        'all_transactions': all_transactions,
        'start_initial': start_initial,
        'end_initial': end_initial
    }
    return render(request, 'income/productIncome/productIncomeHistory.html', context)
