from django.shortcuts import render, redirect, HttpResponse
from django.db.models import Sum, Q
from expenses.models import Expense, BufferExpense
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
import time
from django.core.cache import cache
from User.models import CashAccount
from inventory.models import InventoryProduct, InventoryProductInfo
from credits.models import Credit
from income.models import ProductIncome
from debts.models import Debt


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


def edit_expense_transaction(request, id=0):
    expense = {}
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        back_url = cache.get(f"{buss.id}-{check.id}-edit_product_income_transaction_http_referer")
        if not back_url:
            cache.set(f"{buss.id}-{check.id}-edit_product_income_transaction_http_referer",
                      request.META.get("HTTP_REFERER"), 300)
            back_url = cache.get(f"{buss.id}-{check.id}-edit_product_income_transaction_http_referer")

        try:
            expense = Expense.objects.get(pk=id)
            ca = CashAccount.objects.get(Business__id=buss.id)

            if request.method == 'POST':
                if 'save' in request.POST:
                    quantity = request.POST.get('quantity')
                    price = request.POST.get('price')
                    name = request.POST.get('name')

                    if quantity:
                        quantity = int(quantity)
                    if price:
                        price = int(price)

                    if name:
                        if expense.Name != name:
                            expense.Name = name
                            if expense.Type == 'Stock':
                                try:
                                    product = InventoryProduct.objects.get(Expenses__id=expense.id)
                                    product.Name = name
                                    product.save()
                                    expense.save()
                                    if not price or not quantity:
                                        messages.success(request, 'changes made successfully')
                                except Exception as e:
                                    messages.error(request, f'{e}')
                            else:
                                expense.save()
                    # price and quantity; only mutable(editable) if it's type is not stock
                    if expense.Type != 'Stock':
                        if price:
                            if expense.Price != price:
                                expense.Price = price
                        if quantity:
                            if expense.Quantity != quantity:
                                expense.Quantity = quantity
                        expense.save()

                        messages.success(request, 'changes made successfully')

                if 'delete' in request.POST:
                    if expense.Type != 'Stock':
                        if expense.PMode == 'Credit':
                            messages.warning(request, "Note that this will delete it's credit record too. press"
                                                      " confirm to proceed")
                        else:
                            expense.delete()
                            ca.Value += expense.Price
                            ca.save()
                            messages.success(request, "expense record deleted successfully")

                    elif expense.Type == 'Stock':
                        stock_result = delete_stock_expense(ca, expense)
                        if stock_result == 'success':
                            messages.success(request, "expense record deleted successfully")
                        else:
                            messages.error(request, f"{stock_result}")
                        if back_url:
                            return redirect(f"{back_url}")
                        else:
                            return redirect('/expenses/')

                if 'confirm' in request.POST:
                    on_cred_result = delete_expense_on_credit(ca, expense)
                    if on_cred_result == 'success':
                        messages.success(request, "expense record deleted successfully")
                    else:
                        messages.error(request, f"{on_cred_result}")
                    if back_url:
                        return redirect(f"{back_url}")
                    else:
                        return redirect('/expenses/')

                if 'un-confirm' in request.POST:
                    return redirect(f'/edit_expense_transaction/{id}/')
        except Exception as e:
            messages.error(request, f'{e}')
            return redirect(f'{e}')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'expense': expense,
        'back_url': back_url
    }
    return render(request, 'expense/editExpenseTransaction.html', context)


def delete_expense_on_credit(ca, expense):
    try:
        credit = Credit.objects.get(pk=expense.Credit.id)
        if credit.Amount != expense.Price:
            credit.Amount -= expense.Price
            credit.save()

            ca.Value += expense.Price
            ca.save()
            expense.delete()
        else:
            ca.Value += expense.Price
            expense.delete()
            credit.delete()
            ca.save()

        return 'success'
    except Exception as e:
        return e


def delete_stock_expense(ca, expense):
    # if expense quantity and product's current quantity in inventory don't match,
    # then some of the product has been sold therefore get there sales records
    # and delete them to make sure they don't conflict statement calculations
    # and render the statements unreliable
    try:
        product = InventoryProduct.objects.get(Expenses__id=expense.id)
        prod_info = InventoryProductInfo.objects.get(Product__id=product.id)

        # checking if expense quantity and product's current quantity match
        prod_income = ProductIncome.objects.filter(Product__id=product.id)
        if prod_income.exists():
            for p in prod_income:
                if p.Debt:
                    try:
                        debt_record = Debt.objects.get(pk=p.Debt.id)
                        if debt_record.Amount != p.Amount:
                            debt_record.Amount -= p.Amount
                            debt_record.save()
                            p.delete()

                        else:
                            p.delete()
                            debt_record.delete()
                    except Exception as e:
                        return e
                else:
                    p.delete()

        product.delete()

        if expense.PMode == 'Credit':
            on_cred_result = delete_expense_on_credit(ca, expense)
            if on_cred_result == 'success':
                return 'success'
            else:
                return on_cred_result
        else:
            ca.Value += expense.Price
            ca.save()
            expense.delete()

            return 'success'

    except Exception as e:
        return e
