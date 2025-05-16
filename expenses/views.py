from django.shortcuts import render, redirect, HttpResponse
from django.db.models import Sum, Q
from expenses.models import Expense, BufferExpense
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
import time


# Create your views here.
def get_id(buss):
    ID = Expense.objects.filter(Business=buss).last().id
    return ID


def expenses_table(buss):
    data = Expense.objects.filter(Business=buss).exclude(Type='Asset Expense').order_by('-id')
    return data


def expenses_cash(buss):
    cash_total = (Expense.objects.filter(PMode='Cash', Business=buss).exclude(Type='Asset Expense')
                  .aggregate(Sum('Price')))
    cash_total = cash_total['Price__sum']
    if not cash_total:
        cash_total = 0

    credit_total = (Expense.objects.filter(PMode='Credit', Business=buss).exclude(Type='Asset Expense')
                    .aggregate(Sum('Price')))
    credit_total = credit_total['Price__sum']
    if not credit_total:
        credit_total = 0

    return cash_total, credit_total


def graph(buss):
    amounts = []

    op = Expense.objects.filter(Business=buss, Type='Operational').aggregate(Sum('Price'))
    op = op['Price__sum']
    if not op:
        op = 0

    pe = Expense.objects.filter(Business=buss, Type='Payroll').aggregate(Sum('Price'))
    pe = pe['Price__sum']
    if not pe:
        pe = 0

    se = Expense.objects.filter(Business=buss, Type='Stock').aggregate(Sum('Price'))
    se = se['Price__sum']
    if not se:
        se = 0

    amounts.append(op)
    amounts.append(pe)
    amounts.append(se)
    label = ['O_E', 'P_E', 'S_E']
    return label, amounts


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def expenses_view(request):
    b_id = 0
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        table = expenses_table(buss)
        cash_total, credit_total = expenses_cash(buss)
        label, amounts = graph(buss)
        if request.method == 'POST':
            if 'save' in request.POST:
                name = request.POST.get('name')
                price = request.POST.get('price')
                e_type = request.POST.get('type')
                quantity = request.POST.get('quantity')
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

                b = BufferExpense(Business=buss, Cashier=request.user, Type=e_type, Name=name, Quantity=quantity,
                                  Price=price, PMode=p_mode, Discount=discount, Notes=notes)
                b.save()
                b_id = b.id
                if p_mode == 'Credit' or e_type == 'Stock':
                    return redirect(f'/set_supplier/')
                messages.info(request, 'Set Supplier?')

            if 'No' in request.POST:
                id = request.POST.get("No")
                b = BufferExpense.objects.get(Business=buss, Cashier=request.user, pk=int(id))
                Expense(Business=buss, Cashier=request.User, Name=b.Name, Price=b.Price,
                        Type=b.Name, Quantity=b.Quantity, PMode=b.PMode, Discount=b.Discount,
                        Notes=b.Notes).save()
                b.delete()
                messages.success(request, 'Expense recorded successfully')
                time.sleep(2)
                print('yes')
                return redirect('/expenses/')
            if 'Yes' in request.POST:
                return redirect('/set_supplier/')
    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer"
                            "if the problem persists")
    context = {
        'b_id': b_id,
        'Table': table,
        'Cash_total': cash_total,
        'Credit_total': credit_total,
        'cash': cash_total,
        'debts': credit_total,
        'amounts': amounts,
        'label': label,
    }
    return render(request, 'expense/expenses.html', context)
