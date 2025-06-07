# Create your views here.
from django.shortcuts import render, redirect, HttpResponse
from .models import ProductIncome
from .graphs import income_this_week, daily_total_this_week, cash_credit_this_week
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee, CashAccount
from django.contrib import messages
from inventory.models import InventoryProductInfo
from django.http import StreamingHttpResponse
from .service_income_history import date_initial
from django.core.cache import cache


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def product_income(request):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        table = income_this_week(buss)
        dates, amounts = daily_total_this_week(buss)
        cash, credit = cash_credit_this_week(buss)

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'table': table,
        'amounts': amounts,
        'dates': dates,
        'cash': cash,
        'credit': credit,
    }
    return render(request, 'income/productIncome/productIncome.html', context)


def sorting_data(buss):
    data = ProductIncome.objects.filter(Business=buss)
    sd = {}
    for i in data:
        sd[i.Item] = i.Amount
    sorted_data = dict(sorted(sd.items(), key=lambda x: x[1]))


