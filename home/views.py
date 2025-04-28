from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.contrib import messages
from income.models import *
from expenses.models import *
from inventory.models import *
from debts.models import *
# Create your views here.


@login_required(login_url="/login/")
def home_view(request, *args, **kwargs):
    if request.method == "POST":
        if "refresh cache" in request.POST:
            cache.clear()

    context = {
    }
    return render(request, 'home.html', context)


def display_error(request, code=''):
    # A-S-N-F00 -> active subscription not found
    # S-N-I-S00 -> Service not part of subscription
    # B-P-A-E00 -> Unable to find a business profile you are associated with
    # A-D00 -> Access Denied
    # N-S-U00 -> Not a Super User

    message = ''
    error_codes = {
        'A-S-N-F00': 'You do not have an active subscription',
        'S-N-I-S00': 'This Service in not part of the subscription package',
        'B-P-A-E00': 'Unable to find a business profile you are associated with',
        'A-D00': 'Access Denied',
        'N-S-U00': 'Your are not a super user, your ip address location exposed, good luck running'
    }
    for key, value in error_codes.items():
        if key == code:
            message = value
    context = {
        'message': message
    }
    return render(request, 'errors/errorMessages.html', context)


def get_product_income_trans(trans_id):
    transaction = None
    debt_info = None
    inventory_info = None
    try:
        transaction = ProductIncome.objects.get(pk=trans_id)
        if transaction.PMode == 'Credit':
            debt_info = Debt.objects.get(pk=transaction.Debt.id)
        inventory_info = InventoryProductInfo.objects.get(Product=transaction.Product.id)
    except Exception as e:
        print(f'{e}')
    print('get', debt_info)
    return transaction, inventory_info, debt_info


def get_service_income(trans_id):
    transaction = None
    debt_info = None
    customer_obj = None
    try:
        transaction = ServiceIncome.objects.get(pk=trans_id)
        if transaction.PMode == 'Credit':
            debt_info = Debt.objects.get(pk=transaction.Debt.id)
        if transaction.Customer:
            customer_obj = Customer.objects.get(pk=transaction.Customer.id)
    except Exception as e:
        print(f'{e}')

    return transaction, debt_info, customer_obj


def get_expense_info(trans_id):
    transaction = None
    supplier = None
    credit_info = None
    try:
        transaction = Expense.objects.get(pk=trans_id)
        if transaction.Supplier:
            supplier = Supplier.objects.get(pk=transaction.Supplier.id)
        if transaction.Credit:
            credit_info = Credit.objects.get(pk=transaction.Credit.id)
    except Exception as e:
        print(f'{e}')

    return transaction, supplier, credit_info


def reverse_product_sale_transaction(transaction, inventory_info, debt_info):
    try:
        value = inventory_info.SPrice * transaction.Quantity
        IncomeBuffer(Business=transaction.Business, Cashier=transaction.Cashier,
                     Product=transaction.Product, Code=inventory_info.Code,
                     Quantity=transaction.Quantity, Amount=value).save()

        inventory_info.CurrentQuantity += transaction.Quantity
        inventory_info.CurrentValue += value
        inventory_info.save()
        if transaction.Debt:
            debt_info.delete()
        transaction.delete()

        return 'success'
    except Exception as e:
        return e


def delete_product_sale_transaction(transaction, inventory_info, debt_info):
    try:
        value = inventory_info.SPrice * transaction.Quantity
        inventory_info.CurrentQuantity += transaction.Quantity
        inventory_info.CurrentValue += value
        inventory_info.save()
        if transaction.Debt:
            debt_info.delete()
        transaction.delete()

        return 'success'
    except Exception as e:
        return e


def reverse_service_sale(transaction, debt_info, customer_obj):
    try:
        if transaction.Package:
            ServiceBuffer(Business=transaction.Business, Cashier=transaction.Cashier, Package=transaction.Package,
                          Quantity=transaction.Quantity, Amount=transaction.Amount, PMode=transaction.PMode).save()
        elif transaction.Service:

            ServiceBuffer(Business=transaction.Business, Cashier=transaction.Cashier, Package=transaction.Service,
                          Quantity=transaction.Quantity, Amount=transaction.Amount, PMode=transaction.PMode).save()
        transaction.delete()
        if debt_info:
            debt_info.delete()
        if customer_obj:
            customer_obj.delete()

        return 'success'
    except Exception as e:
        return e


def delete_service_sale(transaction, debt_info, customer_obj):
    try:
        transaction.delete()
        if debt_info:
            debt_info.delete()
        if customer_obj:
            customer_obj.delete()
        return 'success'
    except Exception as e:
        return e


def transaction_info(request, trans_type='', trans_id=0):
    transaction = None
    inventory_info = None
    debt_info = None
    supplier = None
    credit_info = None
    customer_obj = None
    res = ''

    trans_type = trans_type.replace('%', ' ')
    if trans_type == 'product income':
        transaction, inventory_info, debt_info = get_product_income_trans(trans_id)
    elif trans_type == 'service income':
        transaction, debt_info, customer_obj = get_service_income(trans_id)
    elif trans_type == 'expense':
        transaction, supplier, credit_info = get_expense_info(trans_id)

    if not transaction:
        messages.error(request, f'Transaction not found')
    if request.method == 'POST':
        if 'undo' in request.POST:
            if trans_type == 'product income':
                res = reverse_product_sale_transaction(transaction, inventory_info, debt_info)
            elif trans_type == 'service income':
                res = reverse_service_sale(transaction, debt_info, customer_obj)

        if 'delete' in request.POST:
            if trans_type == 'product income':
                res = delete_product_sale_transaction(transaction, inventory_info, debt_info)
            elif trans_type == 'service income':
                res = delete_service_sale(transaction, debt_info, customer_obj)

        if res == 'success':
            return redirect(request.META.get('HTTP_REFERER'))
        else:
            messages.error(request, f'{res}')

    context = {
        'trans_type': trans_type,
        'transaction': transaction,
        'inventory_info': inventory_info,
        'debt_info': debt_info,
        'supplier': supplier,
        'credit_info': credit_info,
        'customer_info': customer_obj
    }
    return render(request, 'management/transactionInformation.html', context)
