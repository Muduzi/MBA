from django.shortcuts import render, redirect, HttpResponse
from _datetime import datetime
# Create your views here.
from django.db.models import Sum, Q
from expenses.models import Expense, BufferExpense, Discount
from inventory.models import InventoryProduct, InventoryDraft
from User.models import CashAccount
from credits.models import Credit, Supplier
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
from django.core.cache import cache
from celery import shared_task


@shared_task()
def get_suppliers(buss_id):
    suppliers = {}

    sup_obj = Supplier.objects.filter(Business__id=buss_id).order_by('-id')
    expenses = Expense.objects.filter(Business_id=buss_id).exclude(Supplier__isnull=True).order_by('-id')
    grand_total = expenses.aggregate(Sum('Price'))
    grand_total = grand_total['Price__sum']
    if not grand_total:
        grand_total = 0

    for s in sup_obj:
        transactions = []
        count = 0
        total = 0
        for e in expenses:
            if s == e.Supplier:
                total += e.Price
                count += 1
                transaction = {'id': e.id, 'Date': e.Date, 'Name': e.Name, 'Quantity': e.Quantity, 'PMode': e.PMode,
                               'Price': e.Price}
                transactions.append(transaction)

        try:
            percentage = round((total/grand_total)*100, 1)
        except ZeroDivisionError:
            percentage = 0

        suppliers[s.id] = {'Name': s.Name, 'Email': s.Email, 'Contact': s.Contact, 'Notes': s.Notes,
                           'Transactions': transactions, 'TransactionsCount': count, 'TransactionsTotal': total,
                           'Percentage': percentage}

    cache.set(f'get_suppliers_{buss_id}', suppliers, 300)

    return suppliers


def suppliers_view(request):
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        get_suppliers.delay(buss.id)
        suppliers = cache.get(f'get_suppliers_{buss.id}')
        if not suppliers:
            suppliers = get_suppliers(buss.id)

    except Employee.DoesNotExist:
        messages.error(request, "failed to process your profile")
        return redirect('/expenses/')

    context = {
        'suppliers': suppliers
    }
    return render(request, 'expense/suppliers.html', context)


@shared_task()
def get_supplier(buss_id, sup_id):
    supplier = {}

    sup_obj = Supplier.objects.get(Business__id=buss_id, pk=sup_id)

    all_expenses = Expense.objects.filter(Business_id=buss_id).exclude(Supplier__isnull=True).order_by('-id')
    grand_total = all_expenses.aggregate(Sum('Price'))
    grand_total = grand_total['Price__sum']
    if not grand_total:
        grand_total = 0

    expenses = Expense.objects.filter(Business_id=buss_id, Supplier__id=sup_obj.id).order_by('-id')
    total = expenses.aggregate(Sum('Price'))
    total = total['Price__sum']
    if not total:
        total = 0

    count = expenses.count()

    transactions = []
    for e in expenses:
        transaction = {'id': e.id, 'Date': e.Date, 'Name': e.Name, 'Quantity': e.Quantity, 'PMode': e.PMode,
                       'Price': e.Price}
        transactions.append(transaction)

    try:
        percentage = round((total/grand_total)*100, 1)
    except ZeroDivisionError:
        percentage = 0

    supplier[sup_obj.id] = {'Name': sup_obj.Name, 'Email': sup_obj.Email, 'Contact': sup_obj.Contact,
                            'Notes': sup_obj.Notes, 'Transactions': transactions, 'TransactionsCount': count,
                            'TransactionsTotal': total, 'Percentage': percentage}

    cache.set(f'get_supplier_{buss_id}_{sup_id}', supplier, 300)

    return supplier


def supplier_view(request, id=0):
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        get_supplier.delay(buss.id, id)
        supplier = cache.get(f'get_supplier_{buss.id}_{id}')
        if not supplier:
            supplier = get_supplier(buss.id, id)

    except Employee.DoesNotExist:
        messages.error(request, "failed to process your profile")
        return redirect('/expenses/')

    context = {
        'supplier': supplier
    }
    return render(request, 'expense/supplier.html', context)
