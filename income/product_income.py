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
from fuzzywuzzy import fuzz


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


def process_selected_product(request, buss, prod_id, quantity):
    try:
        prod = InventoryProduct.objects.get(Business__id=buss.id, pk=prod_id)
        prod_info = InventoryProductInfo.objects.get(Business=buss, Product__id=prod.id)
        a = quantity * prod_info.SPrice
        if prod_info.CurrentQuantity >= quantity:
            b = IncomeBuffer(Business=buss, Cashier=request.user, Code=prod_info.Code, Product=prod, Amount=a,
                             Quantity=quantity)
            b.save()
            return 'success'
        else:
            return f'inventory error: only {prod_info.CurrentQuantity} left in inventory'
    except Exception as e:
        return str(e)


def search_product(buss, name):
    result = None
    try:
        products = InventoryProduct.objects.all()
        result = []
        for p in products:
            ratio = fuzz.partial_ratio(name.lower(), p.Name.lower())
            if ratio > 60:
                prod_info = InventoryProductInfo.objects.get(Business=buss, Product__id=p.id)
                result.append({'id': p.id, 'Name': p.Name, 'Brand': p.Brand, 'Size': p.Size, 'Price': prod_info.SPrice,
                               'ratio': ratio})
        if result:
            result = sorted(result, key=lambda x: x['ratio'], reverse=True)
            return result
        else:
            return "failed to find a product by this name"
    except Exception as e:
        return str(e)


def record_product_sale(request, buss, cash_account,  data, item_count, total, paid, p_mode, discount):
    excess = paid - total
    if excess < 1:
        mean_discount = round(excess / item_count, 1)
    else:
        mean_discount = 0
    for i in data:
        print(i.Code)
        pro_info = InventoryProductInfo.objects.get(Business=buss, Code=i.Code)
        pro_info.CurrentQuantity -= i.Quantity
        pro_info.CurrentValue -= i.Amount

        if discount:
            # mean discount is a negative value hence adding it to amount because:
            # i.Amount - (-mean_discount*i.Quantity); negatives cancel out
            # purchases on credit won't permit discount's
            inc = ProductIncome(Business=buss, Cashier=request.user, Code=pro_info.Code,
                                Product=i.Product, Amount=i.Amount + mean_discount, Quantity=i.Quantity,
                                PMode=p_mode, Discount=discount)
        else:
            inc = ProductIncome(Business=buss, Cashier=request.user, Code=pro_info.Code,
                                Product=i.Product, Amount=i.Amount, Quantity=i.Quantity,
                                PMode=p_mode)

        cash_account.Value += i.Amount

        inc.save()
        pro_info.save()
        cash_account.save()
        i.delete()
    return excess


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def product_sale(request):
    excess = 0
    paid = 0
    search_result = None
    search_name = None
    try:
        check = Employee.objects.get(User=request.user.id)

        buss = check.Business
        data = IncomeBuffer.objects.filter(Business=buss)
        total = data.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0
        item_count = data.count()
        if not item_count:
            item_count = 0

        cash_account = CashAccount.objects.get(Business=buss)

        if request.method == 'POST':
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

            if 'search_name' in request.POST:
                search_name = request.POST.get('search name')

                search_result = search_product(buss, search_name)
                if type(search_result) == str:
                    messages.error(request, f"{search_result}")
                    return redirect('/')

            if 'search product' in request.POST:
                search_name = request.POST.get('search name')

                search_result = search_product(buss, search_name)
                if type(search_result) == str:
                    messages.error(request, f"{search_result}")
                    return redirect('/')

            if 'save selected product' in request.POST:
                selected_product = request.POST.get("selected product")
                quantity = request.POST.get("quantity")
                result = process_selected_product(request, buss, int(selected_product), int(quantity))
                search_result = None
                if result != 'success':
                    messages.success(request, f'{result}')

            if 'finalise' in request.POST:
                paid = request.POST.get('amount')
                p_mode = request.POST.get('PMode')
                discount = request.POST.get('discount')
                paid = int(paid)

                if discount == 'on' and p_mode == 'Credit':
                    p_mode = 'Cash'
                    discount = True
                elif discount == 'on':
                    discount = True
                else:
                    discount = False

                if p_mode == 'Cash':
                    if not total:
                        pass
                    else:
                        if paid < total and not discount:
                            messages.error(request, 'insufficient funds')

                        else:
                            excess = record_product_sale(request, buss, cash_account,  data, item_count,
                                                         total, paid, p_mode, discount)

                elif p_mode == 'Credit':
                    if discount:
                        messages.error(request, "discount on credit purchases is not allowed")
                    else:
                        return redirect('/set_customer/')

            if "generate invoice" in request.POST:
                if data:
                    messages.info(request, "Generate Invoice")
                else:
                    messages.error(request, "add items for the invoice")

            if 'Yes' in request.POST:
                return redirect('/invoice_form/0/products/')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'table': data,
        'search_result': search_result,
        'search_name': search_name,
        'total': total,
        'paid': paid,
        'excess': excess,
    }
    return render(request, 'income/productIncome/productSale.html', context)


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
    return render(request, 'income/productIncome/editProductSale.html', context)
