from django.shortcuts import render, redirect, HttpResponse
from django.db.models import Sum, Q
from expenses.models import Expense, ExpenseAccount, ExpensesGeneralContent
from credits.models import Supplier
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
from statements.ProfitAndLoss import get_tax_year
from datetime import datetime, timezone
from calendar import monthrange
import time
from django.core.cache import cache
from celery import shared_task


@shared_task()
def daily_expenses_this_month(buss):
    date = datetime.now(timezone.utc)
    daily_totals = {}
    expenses_this_month = {}
    suppliers = {}
    date_range = monthrange(date.year, date.month)
    start = datetime(date.year, date.month, 1)
    end = datetime(date.year, date.month, date_range[1])

    for i in range(1, date_range[1]):
        check_date = datetime(date.year, date.month, i)
        data = Expense.objects.filter(Business__id=buss, Date__date=check_date)
        amount = data.aggregate(Sum('Price'))
        amount = amount['Price__sum']
        if not amount:
            amount = 0

        data = Expense.objects.filter(Business__id=buss, PMode='Cash', Date__date=check_date)
        cash = data.aggregate(Sum('Price'))
        cash = cash['Price__sum']
        if not cash:
            cash = 0

        data = Expense.objects.filter(Business__id=buss, PMode='Credit', Date__date=check_date)
        credit = data.aggregate(Sum('Price'))
        credit = credit['Price__sum']
        if not credit:
            credit = 0

        daily_totals[i] = {}
        daily_totals[i]['Amount'] = amount
        daily_totals[i]['Cash'] = cash
        daily_totals[i]['Credit'] = credit

    grand_total = Expense.objects.filter(Business__id=buss, Date__range=(start, end))
    total = grand_total.aggregate(Sum('Price'))
    total = total['Price__sum']
    if not total:
        total = 0

    cash_total = Expense.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
    cash = cash_total.aggregate(Sum('Price'))
    cash = cash['Price__sum']
    if not cash:
        cash = 0

    credit_total = Expense.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
    credit = credit_total.aggregate(Sum('Price'))
    credit = credit['Price__sum']
    if not credit:
        credit = 0

    """"expense accounts"""
    accounts = ExpenseAccount.objects.filter(Business__id=buss)
    for a in accounts:
        expenses = Expense.objects.filter(Business=buss, ExpenseAccount=a, Date__range=(start, end))
        quantity = expenses.aggregate(Sum('Quantity'))
        quantity = quantity['Quantity__sum']

        amount = expenses.aggregate(Sum('Price'))
        amount = amount['Price__sum']
        if not amount:
            amount = 0
        try:
            percentage = round((amount / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        expenses_this_month[a] = {}
        expenses_this_month[a]['Name'] = a.Name
        expenses_this_month[a]['Quantity'] = quantity
        expenses_this_month[a]['Percentage'] = percentage
        expenses_this_month[a]['Amount'] = amount

    expenses = Expense.objects.filter(Business__id=buss, ExpenseAccount__isnull=True, Date__range=(start, end))
    for e in expenses:
        try:
            percentage = round((e.Price / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        expenses_this_month[e] = {}
        expenses_this_month[e]['Name'] = e.Name
        expenses_this_month[e]['Quantity'] = e.Quantity
        expenses_this_month[e]['Percentage'] = percentage
        expenses_this_month[e]['Amount'] = e.Price

    expenses_this_month = dict(sorted(expenses_this_month.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"suppliers"""
    suppliers_obj = Supplier.objects.filter(Business__id=buss).order_by('-id')
    for s in suppliers_obj:
        expenses_record = Expense.objects.filter(Business=buss, Date__range=(start, end), Supplier=s)
        if expenses_record.exists():
            amount = expenses_record.aggregate(Sum('Price'))
            amount = amount['Price__sum']
            if not amount:
                amount = 0
        else:
            amount = 0
        try:
            percentage = round((amount / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        suppliers[s.id] = {}
        suppliers[s.id]['Name'] = s.Name
        suppliers[s.id]['Amount'] = amount
        suppliers[s.id]['Percentage'] = percentage
    suppliers = dict(sorted(suppliers.items(), key=lambda item: item[1]['Amount'], reverse=True))

    # daily_expenses_this_month -> d_e_t_m
    cache.set(str(buss)+'d_e_t_m-total', total, 300)
    cache.set(str(buss) + 'd_e_t_m-cash', cash, 300)
    cache.set(str(buss) + 'd_e_t_m-credit', credit, 300)
    cache.set(str(buss) + 'd_e_t_m-daily_totals', daily_totals, 300)
    cache.set(str(buss) + 'd_e_t_m-suppliers_m', suppliers, 300)
    cache.set(str(buss) + 'd_e_t_m-expenses_this_month', expenses_this_month, 300)

    return total, cash, credit, daily_totals, suppliers, expenses_this_month


@shared_task()
def monthly_expenses_this_year(buss):
    date = datetime.now()
    monthly_expense_records = {}
    expenses_this_year = {}
    suppliers = {}

    this_tax_year = get_tax_year(buss)
    start_ = this_tax_year.TaxYearStart
    end_ = this_tax_year.TaxYearEnd

    start = start_.date()
    for month in range(0, 12):
        if start.month == 12:
            end = datetime(start.year + 1, 1, start.day)
        else:
            end = datetime(start.year, start.month + 1, start.day)

        data = Expense.objects.filter(Business__id=buss, Date__range=(start, end))
        amount = data.aggregate(Sum('Price'))
        amount = amount['Price__sum']
        if not amount:
            amount = 0

        data = Expense.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start, end))
        cash = data.aggregate(Sum('Price'))
        cash = cash['Price__sum']
        if not cash:
            cash = 0

        data = Expense.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start, end))
        credit = data.aggregate(Sum('Price'))
        credit = credit['Price__sum']
        if not credit:
            credit = 0

        monthly_expense_records[start.month] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

        if start.month == 12:
            start = datetime(start.year+1, 1, start.day)
        elif start.month < 12:
            start = datetime(start.year, start.month + 1, start.day)

    grand_total = Expense.objects.filter(Business__id=buss, Date__range=(start_, end_))
    total = grand_total.aggregate(Sum('Price'))
    total = total['Price__sum']
    if not total:
        total = 0

    cash_total = Expense.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start_, end_))
    cash = cash_total.aggregate(Sum('Price'))
    cash = cash['Price__sum']
    if not cash:
        cash = 0

    credit_total = Expense.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start_, end_))
    credit = credit_total.aggregate(Sum('Price'))
    credit = credit['Price__sum']
    if not credit:
        credit = 0

    """"expense accounts"""
    accounts = ExpenseAccount.objects.filter(Business__id=buss)
    for a in accounts:
        expenses = Expense.objects.filter(Business__id=buss, ExpenseAccount=a, Date__range=(start_, end_))
        quantity = expenses.aggregate(Sum('Quantity'))
        quantity = quantity['Quantity__sum']

        amount = expenses.aggregate(Sum('Price'))
        amount = amount['Price__sum']
        if not amount:
            amount = 0
        try:
            percentage = round((amount / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        expenses_this_year[a] = {'Name': a.Name, 'Quantity': quantity, 'Percentage': percentage, 'Amount': amount}

    expenses = Expense.objects.filter(Business__id=buss, ExpenseAccount__isnull=True, Date__range=(start_, end_))
    for e in expenses:
        try:
            percentage = round((e.Price / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        expenses_this_year[e] = {'Name': e.Name, 'Quantity': e.Quantity, 'Percentage': percentage, 'Amount': e.Price}

    expenses_this_year = dict(sorted(expenses_this_year.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"suppliers"""
    suppliers_obj = Supplier.objects.filter(Business__id=buss).order_by('-id')
    for s in suppliers_obj:
        expenses_record = Expense.objects.filter(Business__id=buss, Date__range=(start_, end_), Supplier=s)
        if expenses_record.exists():
            amount = expenses_record.aggregate(Sum('Price'))
            amount = amount['Price__sum']
            if not amount:
                amount = 0
        else:
            amount = 0
        try:
            percentage = round((amount / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        suppliers[s.id] = {'Name': s.Name, 'Amount': amount, 'Percentage': percentage}

    suppliers = dict(sorted(suppliers.items(), key=lambda item: item[1]['Amount'], reverse=True))

    # monthly_expenses_this_year -> m_e_t_y
    cache.set(str(buss) + 'm_e_t_y-total', total, 300)
    cache.set(str(buss) + 'm_e_t_y-cash', cash, 300)
    cache.set(str(buss) + 'm_e_t_y-credit', credit, 300)
    cache.set(str(buss) + 'm_e_t_y-monthly_expense_records', monthly_expense_records, 300)
    cache.set(str(buss) + 'm_e_t_y-suppliers_y', suppliers, 300)
    cache.set(str(buss) + 'm_e_t_y-expenses_this_year', expenses_this_year, 300)

    return total, cash, credit, monthly_expense_records, suppliers, expenses_this_year


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def expenses_dash(request):
    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business.id

        try:
            general_content = ExpensesGeneralContent.objects.get(Business=check.Business, Cashier=user_object)
        except ExpensesGeneralContent.DoesNotExist:
            general_content = None

        # daily_expenses_this_month
        daily_expenses_this_month.delay(buss)
        total_m = cache.get(str(buss) + 'd_e_t_m-total')
        cash_m = cache.get(str(buss) + 'd_e_t_m-cash')
        credit_m = cache.get(str(buss) + 'd_e_t_m-credit')
        daily_totals = cache.get(str(buss) + 'd_e_t_m-daily_totals')
        suppliers_m = cache.get(str(buss) + 'd_e_t_m-suppliers_m')
        expenses_this_month = cache.get(str(buss) + 'd_e_t_m-expenses_this_month')

        if not total_m and cash_m and credit_m and daily_totals and expenses_this_month:
            # total_m, cash_m, credit_m, daily_totals, suppliers_m, expenses_this_month
            # = daily_expenses_this_month(buss)
            return redirect('/expenses_dash/')

        # monthly_expenses_this_year
        monthly_expenses_this_year.delay(buss)
        total_y = cache.get(str(buss) + 'm_e_t_y-total')
        cash_y = cache.get(str(buss) + 'm_e_t_y-cash')
        credit_y = cache.get(str(buss) + 'm_e_t_y-credit')
        monthly_expense_records = cache.get(str(buss) + 'm_e_t_y-monthly_expense_records')
        suppliers_y = cache.get(str(buss) + 'm_e_t_y-suppliers_y')
        expenses_this_year = cache.get(str(buss) + 'm_e_t_y-expenses_this_year')

        if not total_y and cash_y and credit_y and monthly_expense_records and expenses_this_year:
            # total_y, cash_y, credit_y, monthly_expense_records, suppliers_y, expenses_this_year = \
            #   (monthly_expenses_this_year(buss))
            return redirect('/expenses_dash/')

        if request.method == 'POST':
            if 'general_content' in request.POST:
                content = request.POST.get('content')

                if not general_content:
                    general_content = ExpensesGeneralContent(Business=check.Business, Cashier=user_object,
                                                             Choice=content).save()
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
        'daily_totals': daily_totals,
        'expenses_m': expenses_this_month,
        'suppliers_m': suppliers_m,

        'total_y': total_y,
        'cash_y': cash_y,
        'credit_y': credit_y,
        'monthly_totals': monthly_expense_records,
        'expenses_y': expenses_this_year,
        'suppliers_y': suppliers_y,
    }
    return render(request, 'expensesDash.html', context)
