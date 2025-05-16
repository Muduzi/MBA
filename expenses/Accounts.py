from django.shortcuts import render, redirect, HttpResponse
from django.db.models import Sum, Q
from expenses.models import Expense, BufferExpense, ExpenseAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
import time


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def expense_accounts(request):
    b_id = 0
    accounts = {}
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        accounts_obj = ExpenseAccount.objects.filter(Business=buss)

        expenses = Expense.objects.filter(Business=buss, ExpenseAccount__isnull=False)

        total = expenses.aggregate(Sum('Price'))
        total = total['Price__sum']
        if not total:
            total = 0

        for a in accounts_obj:
            expenses_ = Expense.objects.filter(Business=buss, ExpenseAccount=a)
            a_total = expenses_.aggregate(Sum('Price'))
            a_total = a_total['Price__sum']
            if not a_total:
                a_total = 0
            accounts[a] = a_total

        if request.method == 'POST':
            if 'save_account' in request.POST:
                name = request.POST.get('name')
                a_type = request.POST.get('type')
                interval = request.POST.get('interval')
                auto = request.POST.get('auto')
                notes = request.POST.get('notes')

                if auto == "on":
                    auto = True
                else:
                    auto = False
                ExpenseAccount(Business=buss, Cashier=user_obj, Name=name, Type=a_type, Interval=interval,
                               AutoRecord=auto, Notes=notes).save()
                messages.success(request, 'Expense Account created successfully')

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer"
                            "if the problem persists")
    context = {
        'b_id': b_id,
        'accounts': accounts,
        'expenses': expenses,
        'total': total
    }
    return render(request, 'expense/expenseAccounts.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def expense_account(request, id=0):
    b_id = 0
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        account = ExpenseAccount.objects.get(Business=buss, pk=id)
        expenses = Expense.objects.filter(Business=buss, ExpenseAccount=account)

        if request.method == 'POST':
            if 'save_account' in request.POST:
                name = request.POST.get('name')
                a_type = request.POST.get('type')
                interval = request.POST.get('interval')
                auto = request.POST.get('auto')
                notes = request.POST.get('notes')

                if auto == "on":
                    auto = True
                else:
                    auto = False
                if name:
                    if name != account.Name:
                        account.Name = name
                if a_type:
                    if a_type != account.Name:
                        account.Name = a_type
                if interval:
                    if interval != account.Interval:
                        account.Interval = interval
                if auto:
                    if auto != account.AutoRecord:
                        account.AutoRecord = auto
                if notes:
                    if notes != account.Notes:
                        account.Notes = notes
                account.save()
                messages.success(request, 'Account edited successfully')

            if 'save_expense' in request.POST:
                quantity = request.POST.get('quantity')
                price = request.POST.get('price')
                p_mode = request.POST.get('p_mode')
                discount = request.POST.get('discount')
                notes = request.POST.get('notes')
                price = int(price)
                quantity = int(quantity)

                if discount == 'on' and p_mode == 'Credit':
                    p_mode = 'Cash'
                    discount = True
                elif discount == 'on':
                    discount = True
                else:
                    discount = False

                b = BufferExpense(Business=buss, Cashier=user_obj, ExpenseAccount=account, Type=account.Type,
                                  Name=account.Name, Quantity=quantity, Price=price, PMode=p_mode, Discount=discount,
                                  Notes=notes)
                b.save()
                b_id = b.id
                if p_mode == 'Credit' or account.Name == 'Stock':
                    return redirect(f'/set_supplier/')
                messages.info(request, 'Set Supplier?')

            if 'No' in request.POST:
                i_d = request.POST.get("No")
                b = BufferExpense.objects.get(Business=buss, Cashier=user_obj, pk=int(i_d))
                Expense(Business=buss, Cashier=user_obj, ExpenseAccount=b.ExpenseAccount, Name=b.Name,
                        Price=b.Price, Type=b.Type, Quantity=b.Quantity, PMode=b.PMode, Discount=b.Discount,
                        Notes=b.Notes).save()
                b.delete()
                messages.success(request, 'Expense recorded successfully')
                return redirect(f'/expense_account/{id}/')
            if 'Yes' in request.POST:
                return redirect('/set_supplier/')

            if 'delete_account' in request.POST:
                if expenses:
                    messages.warning(request, 'The expense records under this account will not be deleted with'
                                              ' the account are you sure you want to delete')
                else:
                    messages.warning(request, 'Are you sure you want to delete the account')

            if 'confirm' in request.POST:
                if expenses:
                    messages.error(request, 'The expense records under the account will persist')
                    time.sleep(5)
                    for e in expenses:
                        e.ExpenseAccount = None
                        e.save()
                    account.delete()
                    return redirect('/expense_accounts/')
                else:
                    account.delete()
                    return redirect('/expense_accounts/')
            if "un-confirm" in request.POST:
                return redirect(f'/expense_account/{id}/')

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer"
                            "if the problem persists")
    context = {
        'b_id': b_id,
        'account': account,
        'expenses': expenses
    }
    return render(request, 'expense/expenseAccount.html', context)
