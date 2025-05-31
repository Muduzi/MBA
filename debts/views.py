from django.shortcuts import render, redirect, HttpResponse
from .models import Debt, DebtInstallment
from datetime import datetime
from income.models import ProductIncome, ServiceIncome
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from User.decorator import allowed_users
from User.models import Employee
from User.models import CashAccount
# Create your views here.


def today():
    tod = datetime.now()
    return tod


def debt_stats(buss):
    count = Debt.objects.filter(Business=buss).exclude(Status='Paid').values().count()
    total = Debt.objects.filter(Business=buss).exclude(Status='Paid').aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0
    received = Debt.objects.filter(Business=buss, Status='Paying').aggregate(Sum('Received'))
    received = received['Received__sum']
    if not received:
        received = 0
    overdue = Debt.objects.filter(Business=buss, Due__lte=today()).exclude(Status='Paid').aggregate(Sum('Amount'))
    overdue = overdue['Amount__sum']
    if not overdue:
        overdue = 0

    try:
        rec_perc = received / total * 100
        rec_perc = round(rec_perc)
    except ZeroDivisionError:
        rec_perc = 0

    if overdue:
        over_received = (Debt.objects.filter(Business=buss, Due__lte=today()).exclude(Status='Paid').
                         aggregate(Sum('Received')))
        over_received = over_received['Received__sum']

        if over_received:
            overdue -= over_received

    else:
        overdue = 0

    try:
        over_perc = overdue / total * 100
        over_perc = round(over_perc)
    except ZeroDivisionError:
        over_perc = 0

    try:
        expected = total - received
        expe_perc = expected / total * 100
        expe_perc = round(expe_perc)
    except ZeroDivisionError:
        expected = total
        expe_perc = 0

    return count, total, received, rec_perc, expected, expe_perc, overdue, over_perc


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def debt(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)

        buss = check.Business
        data = Debt.objects.filter(Business=buss)
        count, total, received, rec_perc, expected, expe_perc, overdue, over_perc = debt_stats(buss)

        graphd = [rec_perc, expe_perc, over_perc]

        if request.method == 'POST':
            if 'save' in request.POST:
                debtor = request.POST.get('debtor')
                email = request.POST.get('email')
                contact = request.POST.get('contact')
                info = request.POST.get('info')
                c = Debt(Business=buss, Date=datetime.now(), Debtor=debtor, Email=email, Contact=contact, Info=info)
                c.save()
                return redirect('/debt/')

            if 'filter' in request.POST:
                choice = request.POST.get('Show')
                pass

        if id != 0:
            delet = Debt.objects.filter(Business=buss, id=id)
            delet.delete()
            return redirect('/debt/')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'data': data,
        'count': count,
        'total': total,
        'received': received,
        'rec_perc': rec_perc,
        'expected': expected,
        'exp_perc': expe_perc,
        'overdue': overdue,
        'over_perc': over_perc,
        'tod': today(),
        'graphd': graphd,
    }
    return render(request, 'debt.html', context)


"""This function hundles the grunting of credits"""


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def debt_form(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        debt = Debt.objects.get(Business=buss, pk=id)
        data_p = ProductIncome.objects.filter(Business=buss, Debt=debt)
        data_s = ServiceIncome.objects.filter(Business=buss, Debt=debt)
        if request.method == 'POST':
            due = request.POST.get('due')
            debt.Due = due
            debt.save()
            return redirect('/debt/')
    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'debt': debt,
        'data_p': data_p,
        'data_s': data_s
    }
    return render(request, 'debtForm.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def debt_installment(request, id=0):
    remaining = 0
    total = 0
    balance = 0

    try:
        check = Employee.objects.get(User=request.user.id)

        buss = check.Business
        cash_account = CashAccount.objects.get(Business=buss)
        debt = Debt.objects.get(Business=buss, pk=id)
        data_p = ProductIncome.objects.filter(Business=buss, Debt=debt)
        data_s = ServiceIncome.objects.filter(Business=buss, Debt=debt)

        balance = debt.Amount - debt.Received
        if request.method == 'POST':
            if 'save' in request.POST:
                received = request.POST.get('received')
                received = int(received)

                if received:
                    if debt.Status == 'Paid':
                        messages.warning(request, 'Debt already paid in full')
                    else:
                        remaining = debt.Amount - debt.Received
                        if received >= remaining:
                            debt.Received += remaining
                            debt.Status = 'Paid'
                            cash_account.Value += remaining
                            DebtInstallment(Business=buss, Debt=debt, Amount=remaining).save()
                            messages.success(request, "Installment exceeded the remaining debt; excess wont be"
                                                      " reflected in records")
                        elif received == remaining:
                            debt.Received += remaining
                            debt.Status = 'Paid'
                            cash_account.Value += remaining
                            DebtInstallment(Business=buss, Debt=debt, Amount=remaining).save()
                            messages.success(request, "Final installment saved")

                        elif received < remaining:
                            debt.Received += received
                            debt.Status = 'Paying'
                            cash_account.Value += received
                            DebtInstallment(Business=buss, Debt=debt, Amount=received).save()
                            messages.success(request, "Installment saved")
                        debt.save()
                        cash_account.save()
                        return redirect(f'/debt_installment/{id}/')
    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'data_p': data_p,
        'data_s': data_s,
        'debt': debt,
        'balance': balance,
    }
    return render(request, 'debtInstallment.html', context)
