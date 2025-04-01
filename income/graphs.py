from django.shortcuts import render
from datetime import datetime, timedelta
from income.models import ProductIncome
from django.db.models import Sum, Q
# Create your views here.


def income_this_week(buss):
    today = datetime.now()
    delta = timedelta(days=6)
    start = today - delta

    table = ProductIncome.objects.filter(Business=buss, Date__range=(start, today)).order_by('-Date')

    return table


def daily_total_this_week(buss=0):
    today = datetime.now()
    delta = timedelta(days=6)
    delta1 = timedelta(days=1)
    start = today-delta
    amount = 0
    amounts = []
    dates = []

    while start <= today:
        data = ProductIncome.objects.filter(Business=buss, Date__date=start).order_by('-Date')
        amount = data.aggregate(Sum('Amount'))
        amount = amount['Amount__sum']
        if not amount:
            amount = 0
        dates.append(start)
        amounts.append(amount)
        amount = 0
        start += delta1

    return dates, amounts


def cash_credit_this_week(buss=0):
    today = datetime.now()
    delta = timedelta(days=6)
    start = today - delta

    cash_query = ProductIncome.objects.filter(Business=buss, PMode='Cash', Date__range=(start, today))
    cash = cash_query.aggregate(Sum('Amount'))
    cash = cash['Amount__sum']
    credit_query = ProductIncome.objects.filter(Business=buss, PMode='Credit', Date__range=(start, today))
    credit = credit_query.aggregate(Sum('Amount'))
    credit = credit['Amount__sum']

    if not cash:
        cash = 0
    if not credit:
        credit = 0

    return cash, credit

