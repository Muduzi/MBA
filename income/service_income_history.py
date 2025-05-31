from django.shortcuts import render, redirect, HttpResponse
from _datetime import datetime, timedelta, timezone
from calendar import monthrange
from debts.models import Customer
from income.models import ProductIncome, ServiceIncome, Service, Package, Category, ServiceAnnualContent
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from User.models import Employee, TaxYear
from django.contrib import messages
from fuzzywuzzy import fuzz
from django.core.cache import cache
from celery import shared_task


def get_tax_years(buss, start, end):
    start_ = None
    end_ = None
    tax_years = TaxYear.objects.filter(Business__id=buss, TaxYearStart__year__gte=start.year,
                                       TaxYearEnd__year__lte=end.year+1)

    if tax_years:
        if len(tax_years) > 1:
            start_ = tax_years[0].TaxYearStart
            end_ = tax_years[len(tax_years) - 1].TaxYearStart
        else:
            start_ = tax_years[0].TaxYearStart
            end_ = tax_years[0].TaxYearEnd

    return tax_years, start_, end_


def service_income_per_group_history(buss, start, end):
    services = {}
    packages = {}
    categories = {}
    customers = {}

    total = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    grand_total = total.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    """"customers"""
    cust_obj = Customer.objects.filter(Business__id=buss).order_by('-id')
    for c in cust_obj:
        sales_record = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start, end), Customer=c)
        if sales_record.exists():
            amount = sales_record.aggregate(Sum('Amount'))
            amount = amount['Amount__sum']
            if not amount:
                amount = 0
        else:
            amount = 0
        try:
            percentage = round((amount / grand_total) * 100)
        except ZeroDivisionError:
            percentage = 0
        customers[c.id] = {'Name': c.Name, 'Amount': amount, 'Percentage': percentage}
    customers = dict(sorted(customers.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"Income per category"""
    cat_obj = Category.objects.filter(Business__id=buss)
    for c in cat_obj:
        income = ServiceIncome.objects.filter(Q(Business__id=buss), Q(Service__Category=c) | Q(Package__Category=c),
                                              Q(Date__range=(start, end)))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        try:
            percentage = round((amount / grand_total) * 100)
        except ZeroDivisionError:
            percentage = 0
        categories[c.id] = {'Name': c.Name, 'Quantity': quantity, 'Percentage': percentage, 'Amount': amount}
    categories = dict(sorted(categories.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"Income per service"""
    serv_obj = Service.objects.filter(Business__id=buss)
    for s in serv_obj:
        income = ServiceIncome.objects.filter(Business__id=buss, Service=s, Date__range=(start, end))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0
        try:
            percentage = round((amount/grand_total)*100)
        except ZeroDivisionError:
            percentage = 0
        services[s.id] = {'Name': s.Name, 'Category': s.Category.Name, 'Quantity': quantity, 'Percentage': percentage, 'Amount': amount}
    services = dict(sorted(services.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"Income per package"""
    pack_obj = Package.objects.filter(Business__id=buss)
    for p in pack_obj:
        income = ServiceIncome.objects.filter(Business__id=buss, Package=p, Date__range=(start, end))
        quantity = income.count()
        amount = income.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        try:
            percentage = round((amount / grand_total) * 100)
        except ZeroDivisionError:
            percentage = 0
        packages[p.id] = {'Name': p.Name, 'Category': p.Category.Name, 'Quantity': quantity, 'Percentage': percentage,
                          'Amount':  amount}
    packages = dict(sorted(packages.items(), key=lambda item: item[1]['Amount']))

    # service_income_per_group_history -> s_i_p_g_h
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_p_g_h-categories", categories, 300)
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_p_g_h-services", services, 300)
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_p_g_h-packages", packages, 300)
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_p_g_h-customers", customers, 300)

    return categories, services, packages, customers


def service_income_daily_history(buss, year_month):
    income_totals_this_month = {}
    date_range = monthrange(year_month.year, year_month.month)
    start = datetime(year_month.year, year_month.month, 1)
    end = datetime(year_month.year, year_month.month, date_range[1])

    for i in range(1, date_range[1]):
        check_date = datetime(year_month.year, year_month.month, i)
        data = ServiceIncome.objects.filter(Business__id=buss, Date__date=check_date)
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        data = ServiceIncome.objects.filter(Business__id=buss, PMode='Cash', Date__date=check_date)
        cash = data.aggregate(Sum('Amount'))
        cash = cash['Amount__sum']
        if not cash:
            cash = 0

        data = ServiceIncome.objects.filter(Business__id=buss, PMode='Credit', Date__date=check_date)
        credit = data.aggregate(Sum('Amount'))
        credit = credit['Amount__sum']
        if not credit:
            credit = 0

        income_totals_this_month[i] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    all_transactions = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = all_transactions.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    cash_total = ServiceIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
    cash = cash_total.aggregate(Sum('Amount'))
    cash = cash['Amount__sum']
    if not cash:
        cash = 0

    credit_total = ServiceIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
    credit = credit_total.aggregate(Sum('Amount'))
    credit = credit['Amount__sum']
    if not credit:
        credit = 0

    # service_income_daily_history -> s_i_d_h
    # cache.set(f"{buss}_{str(year_month)}_s_i_d_h-total", total, 300)
    # cache.set(f"{buss}_{str(year_month)}_s_i_d_h-cash", cash, 300)
    # cache.set(f"{buss}_{str(year_month)}_s_i_d_h-credit", credit, 300)
    # cache.set(f"{buss}_{str(year_month)}_s_i_d_h-income_totals_this_month", income_totals_this_month, 300)

    return total, cash, credit, income_totals_this_month, all_transactions


def service_income_annual_history(buss, start, end):
    income_year_range = {}

    tax_years, start_, end_ = get_tax_years(buss, start, end)
    for ty in tax_years:
        start_ = ty.TaxYearStart
        end_ = ty.TaxYearEnd

        data = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start_, end_))
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        data = ServiceIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start_, end_))
        cash = data.aggregate(Sum('Amount'))
        cash = cash['Amount__sum']
        if not cash:
            cash = 0

        data = ServiceIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start_, end_))
        credit = data.aggregate(Sum('Amount'))
        credit = credit['Amount__sum']
        if not credit:
            credit = 0

        income_year_range[start_.date()] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    all_transactions = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = all_transactions.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    cash_total = ServiceIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
    cash = cash_total.aggregate(Sum('Amount'))
    cash = cash['Amount__sum']
    if not cash:
        cash = 0

    credit_total = ServiceIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
    credit = credit_total.aggregate(Sum('Amount'))
    credit = credit['Amount__sum']
    if not credit:
        credit = 0

    # service_income_annual_history -> s_i_a_h
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_a_h-total", total, 300)
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_a_h-cash", cash, 300)
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_a_h-credit", credit, 300)
    # cache.set(f"{buss}_{str(start)}-{str(end)}_s_i_a_h-income_year_range", income_year_range, 300)

    return total, cash, credit, income_year_range, all_transactions


def service_income_history(request):
    total = 0
    cash = 0
    credit = 0
    services = {}
    packages = {}
    categories = {}
    customers = {}
    income_record = {}
    all_transactions = {}

    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business.id
        try:
            sales_this_year = ServiceAnnualContent.objects.get(Business__id=buss, Cashier=request.user)
        except ServiceAnnualContent.DoesNotExist:
            sales_this_year = ServiceAnnualContent(Business=check.Business, Cashier=request.user, Choice='Service')
            sales_this_year.save()

        start = cache.get(f'{buss}_{user_object.id}_service_income_history_start')
        end = cache.get(f'{buss}_{user_object.id}_service_income_history_end')

        if start and end:
            difference = abs((start - end)).days

            if difference <= 31:
                total, cash, credit, income_record, all_transactions = service_income_daily_history(buss, start)
                categories, services, packages, customers = service_income_per_group_history(buss, start, end)

            elif difference > 31:
                total, cash, credit, income_record, all_transactions = service_income_annual_history(buss, start, end)

                tax_years, start_, end_ = get_tax_years(buss, start, end)
                categories, services, packages, customers = service_income_per_group_history(buss, start_, end_)

        if request.method == 'POST':
            if 'filter' in request.POST:
                start = request.POST.get('start')
                end = request.POST.get('end')
                # converting html date input into datetime object

                date_format = '%Y-%m-%d'
                start = datetime.strptime(start, date_format).replace(tzinfo=timezone.utc)
                end = datetime.strptime(end, date_format).replace(tzinfo=timezone.utc)

                cache.set(f'{buss}_{user_object.id}_service_income_history_start', start, 300)
                cache.set(f'{buss}_{user_object.id}_service_income_history_end', end, 300)
                difference = abs((start - end)).days

                if difference <= 31:
                    total, cash, credit, income_record, all_transactions = service_income_daily_history(buss, start)
                    categories, services, packages, customers = service_income_per_group_history(buss, start, end)

                elif difference > 31:
                    total, cash, credit, income_record, all_transactions = service_income_annual_history(buss, start, end)

                    tax_years, start_, end_ = get_tax_years(buss, start, end)
                    categories, services, packages, customers = service_income_per_group_history(buss, start_, end_)

            if 'show_content' in request.POST:
                annual_content = request.POST.get('content')
                sales_this_year.Choice = annual_content
                sales_this_year.save()

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")

    context = {
        'total': total,
        'cash': cash,
        'credit': credit,
        'categories': categories,
        'services': services,
        'packages': packages,
        'customers': customers,
        'income_record': income_record,
        "sales_this_year": sales_this_year,
        "all_transactions": all_transactions
    }
    return render(request, 'income/serviceIncome/serviceIncomeHistory.html', context)

