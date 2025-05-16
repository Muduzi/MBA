from django.shortcuts import render, redirect, HttpResponse
from .models import (ServiceIncome, Category, Service, Package, ServiceAnnualContent, ServiceMonthlyContent,
                     ServiceGeneralContent)
from debts.models import Customer
from datetime import datetime, timedelta, timezone
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
from calendar import monthrange
from statements.ProfitAndLoss import get_tax_year
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from celery import shared_task


@shared_task()
def service_income_per_group_this_month(buss):
    date = datetime.now()
    services = {}
    packages = {}
    categories = {}
    customers = {}
    date_range = monthrange(date.year, date.month)
    start = datetime(date.year, date.month, 1)
    end = datetime(date.year, date.month, date_range[1])

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

    # service_income_per_group_this_month -> s_i_p_g_t_m
    cache.set(str(buss) + 's_i_p_g_t_m-categories_m', categories, 300)
    cache.set(str(buss) + 's_i_p_g_t_m-services_m', services, 300)
    cache.set(str(buss) + 's_i_p_g_t_m-packages_m', packages, 300)
    cache.set(str(buss) + 's_i_p_g_t_m-customers_m', customers, 300)

    return categories, services, packages, customers


@shared_task()
def services_daily_records_this_month(buss):
    date = datetime.now(timezone.utc)
    income_this_month = {}
    date_range = monthrange(date.year, date.month)
    start = datetime(date.year, date.month, 1)
    end = datetime(date.year, date.month, date_range[1])

    for i in range(1, date_range[1]):
        check_date = datetime(date.year, date.month, i)
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

        income_this_month[i] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    grand_total = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start, end))
    total = grand_total.aggregate(Sum('Amount'))
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

    # services_daily_records_this_month -> s_d_r_t_m
    cache.set(str(buss) + 's_d_r_t_m-total', total, 300)
    cache.set(str(buss) + 's_d_r_t_m-cash', cash, 300)
    cache.set(str(buss) + 's_d_r_t_m-credit', credit, 300)
    cache.set(str(buss) + 's_d_r_t_m-income_this_month', income_this_month, 300)

    return total, cash, credit, income_this_month


@shared_task()
def service_income_per_group_this_year(buss):
    date = datetime.now(timezone.utc)
    services = {}
    packages = {}
    categories = {}
    customers = {}

    this_tax_year = get_tax_year(buss)
    start = this_tax_year.TaxYearStart
    end = this_tax_year.TaxYearEnd

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
            percentage = round((amount / grand_total) * 100)
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
                              'Amount': amount}
        packages = dict(sorted(packages.items(), key=lambda item: item[1]['Amount']))

    # service_income_per_group_this_year -> s_i_p_g_t_y
    cache.set(str(buss) + 's_i_p_g_t_y-categories_y', categories, 300)
    cache.set(str(buss) + 's_i_p_g_t_y-services_y', services, 300)
    cache.set(str(buss) + 's_i_p_g_t_y-packages_y', packages, 300)
    cache.set(str(buss) + 's_i_p_g_t_y-customers_y', customers, 300)

    return categories, services, packages, customers


@shared_task()
def service_monthly_records_this_year(buss):
    date = datetime.now(timezone.utc)
    income_this_year = {}

    this_tax_year = get_tax_year(buss)
    start_ = this_tax_year.TaxYearStart
    end_ = this_tax_year.TaxYearEnd

    start = start_.date()
    for month in range(0, 12):
        if start.month == 12:
            end = datetime(start.year + 1, 1, start.day)
        else:
            end = datetime(start.year, start.month + 1, start.day)

        data = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start, end))
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0

        data = ServiceIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
        cash = data.aggregate(Sum('Amount'))
        cash = cash['Amount__sum']
        if not cash:
            cash = 0

        data = ServiceIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
        credit = data.aggregate(Sum('Amount'))
        credit = credit['Amount__sum']
        if not credit:
            credit = 0

        income_this_year[start.month] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

        if start.month == 12:
            start = datetime(start.year+1, 1, start.day)
        elif start.month < 12:
            start = datetime(start.year, start.month + 1, start.day)

    """
    date_range = monthrange(datetime.now().year, 12)
    start = datetime(date.year, 1, 1)
    end = datetime(date.year, 12, date_range[1])
    """

    grand_total = ServiceIncome.objects.filter(Business__id=buss, Date__range=(start_, end_))
    total = grand_total.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    cash_total = ServiceIncome.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start_, end_))
    cash = cash_total.aggregate(Sum('Amount'))
    cash = cash['Amount__sum']
    if not cash:
        cash = 0

    credit_total = ServiceIncome.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start_, end_))
    credit = credit_total.aggregate(Sum('Amount'))
    credit = credit['Amount__sum']
    if not credit:
        credit = 0

    # service_monthly_records_this_year -> s_m_r_t_y
    cache.set(str(buss) + 's_m_r_t_y-total', total, 300)
    cache.set(str(buss) + 's_m_r_t_y-cash', cash, 300)
    cache.set(str(buss) + 's_m_r_t_y-credit', credit, 300)
    cache.set(str(buss) + 's_m_r_t_y-income_this_year', income_this_year, 300)

    return total, cash, credit, income_this_year


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def service_income_dash(request):
    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss_id = check.Business.id

        try:
            general_content = ServiceGeneralContent.objects.get(Business__id=buss_id, Cashier=user_object)
        except ServiceGeneralContent.DoesNotExist:
            general_content = ServiceGeneralContent(Business=check.Business, Cashier=user_object, Choice='This Month')
            general_content.save()

        try:
            sales_this_year = ServiceAnnualContent.objects.get(Business__id=buss_id, Cashier=user_object)
        except ServiceAnnualContent.DoesNotExist:
            sales_this_year = ServiceAnnualContent(Business=check.Business, Cashier=user_object, Choice='Service')
            sales_this_year.save()

        try:
            sales_this_month = ServiceMonthlyContent.objects.get(Business__id=buss_id, Cashier=user_object)
        except ServiceMonthlyContent.DoesNotExist:
            sales_this_month = ServiceMonthlyContent(Business=check.Business, Cashier=user_object, Choice='Service')
            sales_this_month.save()

        services_daily_records_this_month.delay(buss_id)
        total_m = cache.get(str(buss_id) + 's_d_r_t_m-total')
        cash_m = cache.get(str(buss_id) + 's_d_r_t_m-cash')
        credit_m = cache.get(str(buss_id) + 's_d_r_t_m-credit')
        income_this_month = cache.get(str(buss_id) + 's_d_r_t_m-income_this_month')

        if total_m and cash_m and credit_m and income_this_month:
            return redirect('/service_dash/')

        service_income_per_group_this_month.delay(buss_id)
        categories_m = cache.get(str(buss_id) + 's_i_p_g_t_m-categories_m')
        services_m = cache.get(str(buss_id) + 's_i_p_g_t_m-services_m')
        packages_m = cache.get(str(buss_id) + 's_i_p_g_t_m-packages_m')
        customers_m = cache.get(str(buss_id) + 's_i_p_g_t_m-customers_m')

        if not categories_m and services_m and packages_m:
            return redirect('/service_dash/')

        service_monthly_records_this_year.delay(buss_id)
        total_y = cache.get(str(buss_id) + 's_m_r_t_y-total')
        cash_y = cache.get(str(buss_id) + 's_m_r_t_y-cash')
        credit_y = cache.get(str(buss_id) + 's_m_r_t_y-credit')
        income_this_year = cache.get(str(buss_id) + 's_m_r_t_y-income_this_year')

        if not total_y and cash_y and credit_y and income_this_year:
            return redirect('/service_dash/')

        service_income_per_group_this_year.delay(buss_id)
        categories_y = cache.get(str(buss_id) + 's_i_p_g_t_y-categories_y')
        services_y = cache.get(str(buss_id) + 's_i_p_g_t_y-services_y')
        packages_y = cache.get(str(buss_id) + 's_i_p_g_t_y-packages_y')
        customers_y = cache.get(str(buss_id) + 's_i_p_g_t_y-customers_y')

        if not categories_m and services_m and packages_m:
            return redirect('/service_dash/')

        if request.method == 'POST':
            if 'general_content' in request.POST:
                content = request.POST.get('content')
                general_content.Choice = content
                general_content.save()

            if 'show_this_year' in request.POST:
                annual_content = request.POST.get('annual_content')
                sales_this_year.Choice = annual_content
                sales_this_year.save()

            if 'show_this_month' in request.POST:
                monthly_content = request.POST.get('monthly_content')
                sales_this_month.Choice = monthly_content
                sales_this_month.save()

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'general_content': general_content,

        'sales_m': sales_this_month,
        'total_m': total_m,
        'cash_m': cash_m,
        'credit_m': credit_m,
        'customers_m': customers_m,
        'income_m': income_this_month,
        'categories_m': categories_m,
        'services_m': services_m,
        'packages_m': packages_m,

        'sales_y': sales_this_year,
        'total_y': total_y,
        'cash_y': cash_y,
        'credit_y': credit_y,
        'customers_y': customers_y,
        'income_y': income_this_year,
        'categories_y': categories_y,
        'services_y': services_y,
        'packages_y': packages_y
    }
    return render(request, 'income/serviceIncome/serviceIncomeDash.html', context)
