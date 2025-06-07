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
from income.service_income_history import get_tax_years
from income.service_income_history import date_initial


def expenses_daily_history(buss, year_month):
    date = datetime.now(timezone.utc)
    daily_totals = {}
    expenses_this_month = {}
    suppliers = {}
    date_range = monthrange(year_month.year, year_month.month)
    start = datetime(year_month.year, year_month.month, 1)
    end = datetime(year_month.year, year_month.month, date_range[1])

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

        daily_totals[i] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    all_transactions = Expense.objects.filter(Business__id=buss, Date__range=(start, end))
    total = all_transactions.aggregate(Sum('Price'))
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
        expenses_this_month[a.id] = {'Name':  a.Name, 'Type': a.Type, 'Quantity': quantity, 'Amount': amount,
                                     'Percentage': percentage}

    expenses = Expense.objects.filter(Business__id=buss, ExpenseAccount__isnull=True, Date__range=(start, end))
    for e in expenses:
        try:
            percentage = round((e.Price / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        expenses_this_month[e.id] = {'Name': e.Name, 'Type': expenses[0].Type, 'Quantity': e.Quantity,
                                     'Percentage': percentage, 'Amount': e.Price}

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

        suppliers[s.id] = {'Name': s.Name, 'Amount': amount, 'Percentage': percentage}

    suppliers = dict(sorted(suppliers.items(), key=lambda item: item[1]['Amount'], reverse=True))

    return total, cash, credit, daily_totals, suppliers, expenses_this_month, all_transactions


def expenses_annual_history(buss, start, end):
    monthly_expense_records = {}
    expenses_year_range = {}
    suppliers = {}

    tax_years, start_, end_ = get_tax_years(buss, start, end)
    for ty in tax_years:
        start_ = ty.TaxYearStart
        end_ = ty.TaxYearEnd

        data = Expense.objects.filter(Business__id=buss, Date__range=(start_, end_))
        amount = data.aggregate(Sum('Price'))
        amount = amount['Price__sum']
        if not amount:
            amount = 0

        data = Expense.objects.filter(Business__id=buss, PMode='Cash', Date__range=(start_, end_))
        cash = data.aggregate(Sum('Price'))
        cash = cash['Price__sum']
        if not cash:
            cash = 0

        data = Expense.objects.filter(Business__id=buss, PMode='Credit', Date__range=(start_, end_))
        credit = data.aggregate(Sum('Price'))
        credit = credit['Price__sum']
        if not credit:
            credit = 0

        monthly_expense_records[start_.date()] = {'Amount': amount, 'Cash': cash, 'Credit': credit}

    all_transactions = Expense.objects.filter(Business__id=buss, Date__range=(start, end))
    total = all_transactions.aggregate(Sum('Price'))
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
        expenses = Expense.objects.filter(Business__id=buss, ExpenseAccount=a, Date__range=(start, end))
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
        expenses_year_range[a.id] = {'Name': a.Name, 'Type': a.Type, 'Quantity': quantity, 'Amount': amount,
                                     'Percentage': percentage}

    expenses = Expense.objects.filter(Business__id=buss, ExpenseAccount__isnull=True, Date__range=(start, end))
    for e in expenses:
        try:
            percentage = round((e.Price / total) * 100)
        except ZeroDivisionError:
            percentage = 0
        expenses_year_range[e.id] = {'Name': e.Name, 'Type': expenses[0].Type, 'Quantity': e.Quantity,
                                     'Percentage': percentage, 'Amount': e.Price}

    expenses_year_range = dict(sorted(expenses_year_range.items(), key=lambda item: item[1]['Amount'], reverse=True))

    """"suppliers"""
    suppliers_obj = Supplier.objects.filter(Business__id=buss).order_by('-id')
    for s in suppliers_obj:
        expenses_record = Expense.objects.filter(Business__id=buss, Date__range=(start, end), Supplier=s)
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

    return total, cash, credit, monthly_expense_records, suppliers, expenses_year_range, all_transactions


def expense_history(request):
    total = 0
    cash = 0
    credit = 0
    totals = {}
    suppliers = {}
    expense_record = {}
    all_transactions = {}
    start_initial = None
    end_initial = None

    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business.id

        start = cache.get(f'{buss}_{user_object.id}_expense_history_start')
        end = cache.get(f'{buss}_{user_object.id}_expense_history_end')
        if start and end:
            difference = abs((start - end).days)

            if difference <= 31:
                total, cash, credit, totals, suppliers, expense_record, all_transactions = expenses_daily_history(buss, start)

            elif difference > 31:
                total, cash, credit, totals, suppliers, expense_record, all_transactions = expenses_annual_history(buss, start, end)

            start_initial = date_initial(start)
            end_initial = date_initial(end)

        if 'filter' in request.POST:
            start = request.POST.get('start')
            end = request.POST.get('end')
            # converting html date input into datetime object

            date_format = '%Y-%m-%d'
            start = datetime.strptime(start, date_format).replace(tzinfo=timezone.utc)
            end = datetime.strptime(end, date_format).replace(tzinfo=timezone.utc)

            cache.set(f'{buss}_{user_object.id}_expense_history_start', start, 300)
            cache.set(f'{buss}_{user_object.id}_expense_history_end', end, 300)

            difference = abs((start - end).days)

            if difference <= 31:
                total, cash, credit, totals, suppliers, expense_record, all_transactions = expenses_daily_history(buss, start)

            elif difference > 31:
                total, cash, credit, totals, suppliers, expense_record, all_transactions = expenses_annual_history(buss, start, end)

            start_initial = date_initial(start)
            end_initial = date_initial(end)

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'total': total,
        'cash': cash,
        'credit': credit,
        'totals': totals,
        'suppliers': suppliers,
        'expense_record': expense_record,
        'all_transactions':  all_transactions,
        'start_initial': start_initial,
        'end_initial': end_initial
    }
    return render(request, 'expense/expensesHistory.html', context)
