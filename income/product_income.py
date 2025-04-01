from django.shortcuts import render, redirect, HttpResponse
from _datetime import (datetime, timedelta)
from inventory.models import InventoryProduct, InventoryProductInfo
from income.models import (ProductIncome, IncomeBuffer)
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from User.models import Employee
from User.models import CashAccount
from django.contrib import messages


def get_id(param, business):
    ID = param.objects.filter(Business=business).last().id
    return ID


def now():
    now = datetime.now()
    return now


def process_buy_id(buss, request, code, quantity):
    try:
        pro_info = InventoryProductInfo.objects.get(Business=buss, Code=code)
        prod = InventoryProduct.objects.get(Business=buss, pk=pro_info.Product.id)
        a = quantity * pro_info.SPrice
        if pro_info.CurrentQuantity >= quantity:
            b = IncomeBuffer(Business=buss, Cashier=request.user, Code=pro_info.Code, Product=prod, Amount=a,
                             Quantity=quantity)
            b.save()

            return 'success'
        else:
            return 'inventory error'
    except InventoryProductInfo.DoesNotExist:
        return 'unable to find the product'


def process_buy_name(buss, request, name, brand, size, quantity):
    try:
        prod = InventoryProduct.objects.get(Q(Business=buss), Q(Name__contains=name) & Q(Brand__contains=brand) & Q(Size__contains=size))
        pro_info = InventoryProductInfo.objects.get(Business=buss, Product=prod.id)

        a = quantity * pro_info.SPrice
        if pro_info.CurrentQuantity >= quantity:
            b = IncomeBuffer(Business=buss, Cashier=request.user, Code=pro_info.Code, Product=prod, Amount=a, Quantity=quantity)
            b.save()
            return 'success'
        else:
            return f'inventory error: only {pro_info.CurrentQuantity} left in inventory'
    except InventoryProduct.DoesNotExist:
        return 'unable to find the product in inventory'


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def product_sale(request):
    excess = 0
    paid = 0
    try:
        check = Employee.objects.get(User=request.user.id)

        buss = check.Business
        data = IncomeBuffer.objects.filter(Business=buss)
        total = data.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        cash_account = CashAccount.objects.get(Business=buss)

        if request.method == 'POST':
            if 'save' in request.POST:
                name = request.POST.get('name')
                brand = request.POST.get('brand')
                size = request.POST.get('size')
                quantity = request.POST.get('quantity')
                quantity = int(quantity)
                result = process_buy_name(buss, request, name, brand, size, quantity)
                if result == 'success':
                    return redirect('/product_sale/')

                else:
                    messages.error(request, f'{result}')

            if 'save_by_code' in request.POST:
                code = request.POST.get('code')
                quantity = request.POST.get('quantity')

                quantity = int(quantity)
                result = process_buy_id(buss, request, code, quantity)

                if result == 'success':
                    return redirect('/product_sale/')

                elif result == 'inventory error':
                    messages.error(request, 'Not enough items in inventory')

                elif 'unable to find the product':
                    messages.error(request, "Unable to find a product that matches the code")

            if 'finalise' in request.POST:
                paid = request.POST.get('amount')
                p_mode = request.POST.get('PMode')
                paid = int(paid)
                if p_mode == 'Cash':
                    if not total:
                        pass
                    else:
                        if paid < total:
                            messages.error(request, 'insufficient funds')

                        elif paid >= total:
                            excess = paid - total
                            for i in data:
                                print(i.Code)
                                pro_info = InventoryProductInfo.objects.get(Business=buss, Code=i.Code)
                                pro_info.CurrentQuantity -= i.Quantity
                                pro_info.CurrentValue -= i.Amount

                                inc = ProductIncome(Business=buss, Cashier=request.user, Code=pro_info.Code,
                                                    Product=i.Product, Amount=i.Amount, Quantity=i.Quantity,
                                                    PMode=p_mode)

                                cash_account.Value += i.Amount

                                inc.save()
                                pro_info.save()
                                cash_account.save()
                                i.delete()

                elif p_mode == 'Credit':
                    return redirect('/set_customer/')

            if 'invoice' in request.POST:
                return redirect('/invoice_form/0/products/')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'table': data,
        'total': total,
        'paid': paid,
        'excess': excess
    }
    return render(request, 'productSale.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def edit_product_sale(request, id):
    try:
        check = Employee.objects.get(User=request.user.id)

        buss = check.Business
        buff_obj = IncomeBuffer.objects.get(Business=buss, pk=id)

        if request.method == 'POST':
            if 'save' in request.POST:
                quantity = request.POST.get('Quantity')
                quantity = int(quantity)
                check_item = InventoryProductInfo.objects.filter(Business=buss, Code=buff_obj.Code)
                if check_item:
                    for c in check_item:
                        a = quantity * c.SPrice
                        if c.CurrentQuantity >= quantity:
                            buff_obj.Quantity = quantity
                            buff_obj.Amount = a
                            buff_obj.save()
                            return redirect('/product_sale/')
                        elif c.Current_stock < quantity:
                            return redirect('/invent_error/')

            elif 'delete' in request.POST:
                buff_obj.delete()
                return redirect('/product_sale/')
    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'buff_obj': buff_obj
    }
    return render(request, 'editProductSale.html', context)
