# Create your views here.
from django.shortcuts import render, redirect, HttpResponse
from .models import ServiceIncome, ServiceBuffer, ProductIncome, IncomeBuffer
from inventory.models import InventoryProductInfo
from debts.models import Debt, Customer
from User.models import Employee, Business
from django.contrib import messages
from django.db.models import Sum, Q
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from User.models import CashAccount
from django.core.cache import cache
from celery import shared_task


@shared_task()
def get_customers(buss_id):
    customers = {}

    cust_obj = Customer.objects.filter(Business__id=buss_id).order_by('-id')
    serv_inc = ServiceIncome.objects.filter(Business_id=buss_id).exclude(Customer__isnull=True).order_by('-id')
    grand_total = serv_inc.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    for c in cust_obj:
        transactions = []
        count = 0
        total = 0
        for s in serv_inc:
            if c == s.Customer:
                total += s.Amount
                count += 1
                name = ''
                if s.Package:
                    name = s.Package.Name
                elif s.Service:
                    name = s.Service.Name

                transaction = {'id': s.id, 'Date': s.Date, 'Name': name, 'Quantity': s.Quantity, 'PMode': s.PMode,
                               'Amount': s.Amount}

                transactions.append(transaction)

        try:
            percentage = round((total/grand_total)*100, 1)
        except ZeroDivisionError:
            percentage = 0

        customers[c.id] = {'Name': c.Name, 'Email': c.Email, 'Contact': c.Contact, 'Notes': c.Notes,
                           'Transactions': transactions, 'TransactionsCount': count, 'TransactionsTotal': total,
                           'Percentage': percentage}

    cache.set(f'get_customers_{buss_id}', customers, 300)

    return customers


def customers_view(request):
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        get_customers.delay(buss.id)
        customers = cache.get(f'get_customers_{buss.id}')
        if not customers:
            customers = get_customers(buss.id)

    except Employee.DoesNotExist:
        messages.error(request, "failed to process your profile")
        return redirect('/service_income/')

    context = {
        'customers': customers
    }
    return render(request, 'income/customers.html', context)


@shared_task()
def get_customer(buss_id, cust_id):
    customer = {}

    cust_obj = Customer.objects.get(Business__id=buss_id, pk=cust_id)

    all_serv_inc = ServiceIncome.objects.filter(Business_id=buss_id).exclude(Customer__isnull=True).order_by('-id')
    grand_total = all_serv_inc.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    serv_inc = ServiceIncome.objects.filter(Business_id=buss_id, Customer__id=cust_obj.id).order_by('-id')
    total = serv_inc.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    count = serv_inc.count()

    transactions = []
    for a in serv_inc:
        name = ''
        if a.Package:
            name = a.Package.Name
        elif a.Service:
            name = a.Service.Name

        transaction = {'id': a.id, 'Date': a.Date, 'Name': name, 'Quantity': a.Quantity, 'PMode': a.PMode,
                       'Amount': a.Amount}
        transactions.append(transaction)

    try:
        percentage = round((total/grand_total)*100, 1)
    except ZeroDivisionError:
        percentage = 0

    customer[cust_obj.id] = {'Name': cust_obj.Name, 'Email': cust_obj.Email, 'Contact': cust_obj.Contact,
                             'Notes': cust_obj.Notes, 'Transactions': transactions, 'TransactionsCount': count,
                             'TransactionsTotal': total, 'Percentage': percentage}

    cache.set(f'get_customer_{buss_id}_{cust_id}', customer, 300)

    return customer


def customer_view(request, id=0):
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        get_customer.delay(buss.id, id)
        customer = cache.get(f'get_customer_{buss.id}_{id}')
        if not customer:
            customer = get_customer(buss.id, id)

    except Employee.DoesNotExist:
        messages.error(request, "failed to process your profile")
        return redirect('/service_income/')

    context = {
        'customer': customer
    }
    return render(request, 'income/customer.html', context)
