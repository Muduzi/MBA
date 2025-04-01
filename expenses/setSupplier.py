from django.shortcuts import render,redirect, HttpResponse
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


def find_supplier(buss, search_item):
    search_result = Supplier.objects.filter(Business=buss, Name__contains=search_item)

    return search_result


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def set_supplier(request):
    search_result = {}
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business
        cash_account = CashAccount.objects.get(Business=buss)

        data = BufferExpense.objects.filter(Business=buss, Cashier=user_obj)
        suppliers = Supplier.objects.filter(Business=buss)

        if data.exists():
            total = data.aggregate(Sum('Price'))
            total = total['Price__sum']
            if not total:
                total = 0

            if request.method == 'POST':
                if 'newSupplier' in request.POST:
                    name = request.POST.get('name')
                    email = request.POST.get('email')
                    contact = request.POST.get('contact')
                    notes = request.POST.get('notes')

                    try:
                        supplier = Supplier.objects.get(Business=buss, Name=name, Email=email)
                        result = set_expense(buss, cash_account, user_obj, supplier, data, total)
                    except Supplier.DoesNotExist:
                        supplier = Supplier(Business=buss, Name=name, Email=email, Contact=contact, Notes=notes)
                        supplier.save()
                        result = set_expense(buss, cash_account, user_obj, supplier, data, total)

                    if type(result) == str:
                        if result == 'success':
                            search_result = None
                            messages.success(request, 'supplier added successfully')
                        elif result == 'error':
                            messages.error(request, f'{result}')
                    else:
                        return redirect(f'/credit_form/{result.id}/')

                if 'search' in request.POST:
                    search_item = request.POST.get('search')

                    search_result = find_supplier(buss, search_item)

                    if not search_result:
                        messages.error(request, 'Customer profile not found; make sure you types the name correctly')

                if 'selectedSupplier' in request.POST:
                    search_item = request.POST.get('search')
                    supplier = request.POST.get('supplier')

                    if search_item:
                        search_result = find_supplier(buss, search_item)

                        if not search_result:
                            messages.error(request,
                                           'Customer profile not found; make sure you types the name correctly')

                    elif suppliers:
                        supplier = int(supplier)
                        for s in suppliers:
                            if s.id == supplier:
                                if data:
                                    search_result = None
                                    result = set_expense(buss, cash_account, user_obj, s, data, total)
                                    if type(result) == str:
                                        if result == 'success':
                                            search_result = None
                                            messages.success(request, 'supplier added successfully')
                                        elif result == 'error':
                                            messages.error(request, f'{result}')
                                        elif result == 'insufficient funds':
                                            messages.error(request, "insufficient funds in the 'Cash Account'")
                                    else:
                                        return redirect(f'/credit_form/{result.id}/')

                elif 'cancel' in request.POST:
                    data.delete()
                    return redirect('/expenses/')
        else:
            return redirect('/buffer_expense/')
    except Employee.DoesNotExist:
        return HttpResponse("staff does not exists error at expense. Please contact the developer for help")

    context = {
        'data': data,
        'Amount': total,
        'suppliers': suppliers,
        'search_result': search_result
    }
    return render(request, 'setSupplier.html', context)


def set_expense(buss, cash_account, user_obj, supplier, data, total):
    for i in data:
        if i.PMode == 'Cash':
            if cash_account.Value > i.Price:
                if i.ExpenseAccount:
                    e = Expense(Business=buss, Cashier=user_obj, Supplier=supplier, ExpenseAccount=i.ExpenseAccount,
                                Name=i.Name, Price=i.Price, Type=i.Type, Quantity=i.Quantity, PMode=i.PMode,
                                Discount=i.Discount, Notes=i.Notes)
                else:
                    e = Expense(Business=buss, Cashier=user_obj, Supplier=supplier, Name=i.Name, Price=i.Price,
                                Type=i.Type, Quantity=i.Quantity, PMode=i.PMode, Discount=i.Discount, Notes=i.Notes)
                e.save()
                cash_account.Value -= i.Price
                cash_account.save()
                if i.Type == 'Stock':
                    InventoryDraft(Business=buss, Expenses=e, Name=i.Name, InitialQuantity=i.Quantity,
                                   Cost=i.Price).save()
            else:
                return 'insufficient funds'

        elif i.PMode == 'Credit':
            result = set_expense_credit(buss, user_obj, supplier, data, total)

            return result
        print(data)
    data.delete()
    return 'success'


def set_expense_credit(buss, user_obj, supplier, data, total):
    credit = Credit(Business=buss, Supplier=supplier, Amount=total, Status='Not Paid', Sent=0, Notes=Supplier.Notes)
    credit.save()
    for i in data:
        try:
            if i.ExpenseAccount:
                e = Expense(Business=buss, Cashier=user_obj, Supplier=supplier, Credit=credit,
                            ExpenseAccount=i.ExpenseAccount, Name=i.Name, Price=i.Price, Type=i.Type,
                            Quantity=i.Quantity, PMode=i.PMode, Discount=i.Discount, Notes=i.Notes)
            else:
                e = Expense(Business=buss, Cashier=user_obj, Supplier=supplier, Credit=credit, Name=i.Name,
                            Price=i.Price, Type=i.Type, Quantity=i.Quantity, PMode=i.PMode, Discount=i.Discount,
                            Notes=i.Notes)
            e.save()
        except Exception as e:
            return f'encountered an error:{e}'
        if i.Type == 'Stock':
            InventoryDraft(Business=buss, Expenses=e, Name=i.Name, InitialQuantity=i.Quantity, Cost=i.Price).save()

    data.delete()
    return credit
