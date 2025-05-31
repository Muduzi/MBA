from django.shortcuts import render, redirect, HttpResponse
from .models import Credit
from datetime import datetime
from expenses.models import Expense
from credits.models import Supplier, CreditInstallment
from inventory.models import InventoryDraft
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from User.decorator import allowed_users
from User.models import Employee
from User.models import CoreSettings, CashAccount

# Create your views here.


def today():
    tod = datetime.now()
    return tod


def credit_stats(buss):
    count = Credit.objects.filter(Business__id=buss).exclude(Status='Paid').values().count()
    total = Credit.objects.filter(Business__id=buss).exclude(Status='Paid').aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0
    sent = Credit.objects.filter(Business__id=buss, Status='Paying').aggregate(Sum('Sent'))
    sent = sent['Sent__sum']
    if not sent:
        sent = 0
    overdue = Credit.objects.filter(Business__id=buss, Due__lte=today()).exclude(Status='Paid').aggregate(Sum('Amount'))
    overdue = overdue['Amount__sum']
    if not overdue:
        overdue = 0

    try:
        sent_perc = sent / total * 100
        sent_perc = round(sent_perc)
    except ZeroDivisionError:
        sent_perc = 0

    if overdue:
        over_sent = (Credit.objects.filter(Business__id=buss, Due__lte=today()).exclude(Status='Paid').
                     aggregate(Sum('Sent')))
        over_sent = over_sent['Sent__sum']

        if over_sent:
            overdue -= over_sent
            print(overdue)

    else:
        overdue = 0

    try:
        over_perc = overdue / total * 100
        over_perc = round(over_perc)
    except ZeroDivisionError:
        over_perc = 0

    try:
        remaining = total - sent
        rem_perc = remaining / total * 100
        rem_perc = round(rem_perc)
    except ZeroDivisionError:
        remaining = total
        rem_perc = 0

    return count, total, sent, sent_perc, overdue, over_perc, remaining, rem_perc


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def credit_view(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business.id

        data = Credit.objects.filter(Business__id=buss).order_by('-id')
        count, total, sent, sent_perc, overdue, over_perc, remaining, rem_perc = credit_stats(buss)
        graphd = [sent_perc, rem_perc, over_perc]
        if request.method == 'POST':
            if 'save' in request.POST:
                creditor = request.POST.get('creditor')
                email = request.POST.get('email')
                contact = request.POST.get('contact')
                info = request.POST.get('info')
                supplier = Supplier(Business=check.Business, Name=creditor, Email=email, Contact=contact, Info=info)
                supplier.save()

                d = Credit(Date=datetime.now(), Business=check.Business, Supplier=supplier, Info=info)
                d.save()
                return redirect('/credit/')

            if 'filter' in request.POST:
                    choice = request.POST.get('Show')
                    pass
        if id != 0:
            delet = Credit.objects.filter(Business=buss, id=id)
            delet.delete()
            return redirect('/credit/')

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")
    context = {
        'data': data,
        'count': count,
        'total': total,
        'sent': sent,
        'sent_perc': sent_perc,
        'overdue': overdue,
        'over_perc': over_perc,
        'remaining': remaining,
        'rem_perc': rem_perc,
        'tod': today(),
        'graphd': graphd
    }
    return render(request, 'expense/credit/credit.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def credit_form(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        try:
            credit = Credit.objects.get(Business=buss, pk=id)
            if credit.Due:
                if len(str(credit.Due.day)) == 1:
                    day = f'0{credit.Due.day}'
                else:
                    day = credit.Due.day
                if len(str(credit.Due.month)) == 1:
                    month = f'0{credit.Due.month}'
                else:
                    month = credit.Due.month

                due_date = f"{credit.Due.year}-{month}-{day}"
            else:
                due_date = None

            data = Expense.objects.filter(Business=buss, Credit__id=credit.id)
            total = credit.Amount
            if request.method == 'POST':
                due = request.POST.get('due')
                credit.Due = due
                credit.Status = 'Not Paid'
                credit.save()
                if data[0].Type == 'Stock':
                    draft = InventoryDraft.objects.filter(Business=buss, Expenses=data[0])
                    if draft.exists():
                        if draft.count() > 1:
                            return redirect('/add_inventory/')
                        elif draft.count() == 1:
                            return redirect(f'/add_inventory/{draft[0].id}')
                else:
                    return redirect('/credit/')
        except Credit.DeosNotExist:
            messages.error(request, "failed to get the credit record")
            return redirect(request.META.get('HTTP_REFERER'))
    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")

    context = {
        'credit': credit,
        'data': data,
        'total': total,
        'due_date': due_date
    }
    return render(request, 'expense/credit/creditForm.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def credit_installment(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        cash_account = CashAccount.objects.get(Business=buss)
        credit = Credit.objects.get(Business=buss, pk=id)
        data = Expense.objects.filter(Business=buss, Supplier=credit.Supplier.id, PMode='Credit')
        remaining = credit.Amount - credit.Sent
        if not remaining:
            remaining = 0
        if request.method == 'POST':
            if 'save' in request.POST:
                send = request.POST.get('send')
                send = int(send)

                if send:
                    if credit.Status == 'Paid':
                        messages.info(request, 'Credit already paid in full')
                    else:
                        if cash_account.Value >= send:
                            remainder = credit.Amount-credit.Sent
                            if send > remainder:
                                credit.Sent += remainder
                                credit.Status = 'Paid'
                                cash_account.Value -= remainder
                                CreditInstallment(Business=buss, Debt=credit, Amount=remaining).save()
                                messages.success(request, "Credit repaid successfully")
                            elif send == remainder:
                                credit.Sent += remainder
                                credit.Status = 'Paid'
                                cash_account.Value -= remainder
                                CreditInstallment(Business=buss, Debt=credit, Amount=remaining).save()
                                messages.success(request, "Credit repaid successfully")
                            else:
                                credit.Sent += send
                                credit.Status = 'Paying'
                                cash_account.Value -= send
                                CreditInstallment(Business=buss, Debt=credit, Amount=send).save()
                                messages.success(request, "Credit payment recorded")
                            credit.save()
                            cash_account.save()
                            return redirect(f'/credit_installment/{id}/')
                        else:
                            messages.error(request, "You don't have enough funds to repay the debt")

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")

    context = {
        'data': data,
        'credit': credit,
        'remaining': remaining
    }
    return render(request, 'expense/credit/creditInstallment.html', context)
