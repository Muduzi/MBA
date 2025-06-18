from django.shortcuts import render, redirect, HttpResponse
from _datetime import datetime
# Create your views here.
from .models import InventoryCategory, InventoryProduct, InventoryProductInfo, InventoryDraft
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from User.models import Employee
from expenses.models import Expense
from django.contrib.auth.models import User
from django.core.cache import cache
from celery import shared_task


@shared_task()
def inventory_data(buss):
    stock_delta = 0
    initial = 0
    current = 0
    data = {}
    stock_count = 0
    available_prod = 0
    unavailable_prod = 0

    products = InventoryProduct.objects.filter(Business__id=buss).order_by('-id')
    product_info = InventoryProductInfo.objects.filter(Business__id=buss).order_by('-id')
    categories = InventoryCategory.objects.filter(Business__id=buss)

    cat_count = categories.count()
    if not cat_count:
        cat_count = 0
    stock_value = product_info.aggregate(Sum('CurrentValue'))
    stock_value = stock_value['CurrentValue__sum']
    if not stock_value:
        stock_value = 0
    for c in categories:
        for p in products:
            for pi in product_info:
                if p.Category == c and p == pi.Product:
                    data[p.id] = {}
                    data[p.id]['id'] = p.id
                    data[p.id]['Name'] = p.Name
                    data[p.id]['Code'] = pi.Code
                    data[p.id]['Category'] = c.Name
                    data[p.id]['Brand'] = p.Brand
                    data[p.id]['Size'] = p.Size
                    data[p.id]['SPrice'] = pi.SPrice
                    data[p.id]['Quantity'] = pi.CurrentQuantity
                    data[p.id]['Value'] = pi.CurrentValue
                    data[p.id]['ExpiryDate'] = p.ExpiryDate
                    data[p.id]['Close'] = pi.Close
                    try:
                        reorder = (pi.InitialQuantity/pi.CurrentQuantity*100)
                    except ZeroDivisionError:
                        reorder = 0
                    data[p.id]['reorder'] = reorder

                    if pi.Close == True:
                        unavailable_prod += 1
                    else:
                        available_prod += 1
                        stock_count += pi.CurrentQuantity
    if not stock_count:
        stock_count = 0
    if data:
        data = dict(sorted(data.items(), key=lambda item: item[1]['id'], reverse=True))
    prod_delta = unavailable_prod - available_prod
    if product_info:
        for i in product_info:
            initial += i.InitialQuantity
            current += i.CurrentQuantity
    stock_delta += current - initial
    try:
        current_percentage = current/initial*100
        current_remainder = 100 - current_percentage
    except ZeroDivisionError:
        current_percentage = 0
        current_remainder = 0

    cache.set(str(buss) + 'data', data, 300)
    cache.set(str(buss) + 'initial', initial, 300)
    cache.set(str(buss) + 'current', current, 300)
    cache.set(str(buss) + 'cat_count', cat_count, 300)
    cache.set(str(buss) + 'available_prod', available_prod, 300)
    cache.set(str(buss) + 'unavailable_prod', unavailable_prod, 300)
    cache.set(str(buss) + 'prod_delta', prod_delta, 300)
    cache.set(str(buss) + 'stock_value', stock_value, 300)
    cache.set(str(buss) + 'stock_delta', stock_delta, 300)
    cache.set(str(buss) + 'stock_count', stock_count, 300)
    cache.set(str(buss) + 'current_percentage', current_percentage, 300)
    cache.set(str(buss) + 'current_remainder', current_remainder, 300)

    return (data, initial, current, cat_count, available_prod, unavailable_prod, prod_delta,
            stock_value, stock_delta, stock_count, current_percentage, current_remainder)


@shared_task()
def least_performing(buss):
    prod_performance = {}
    data = {}
    order = {}
    products = InventoryProduct.objects.filter(Business__id=buss).order_by('-id')
    product_info = InventoryProductInfo.objects.filter(Business__id=buss).order_by('-id')

    for p in products:
        for pi in product_info:
            if p == pi.Product:
                delta = ((pi.InitialQuantity - pi.CurrentQuantity)/pi.InitialQuantity)

                rate = round((delta * 100), 1)

                days1 = p.Date.day
                months1 = p.Date.month
                years1 = p.Date.year

                today = datetime.now()
                days2 = today.day
                months2 = today.month
                years2 = today.year

                days = ((years2-years1)*365) + ((months2-months1)*30) + (days2-days1)

                data[pi.Code] = {}
                data[pi.Code]['Name'] = p.Name
                data[pi.Code]['Size'] = p.Size
                data[pi.Code]['days'] = days
                data[pi.Code]['rate'] = rate

                try:

                    order[pi.Code] = days/rate
                except ZeroDivisionError:
                    order[pi.Code] = 0

    for i in range(len(order)):
        max_prod = min(zip(order.values(), order.keys()))[1]
        for a, b in data.items():
            if a == max_prod:
                prod_performance[a] = b
                del order[max_prod]

    cache.set(str(buss) + 'prod_performance', prod_performance)

    return prod_performance


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def inventory_view(request, id=0, r=''):
    item = {}
    product = None
    product_info = None
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business.id

        back_url = cache.get(f"{buss}-{check.id}-inventory_view_http_referer")
        if not back_url:
            cache.set(f"{buss}-{check.id}-inventory_view_http_referer", request.META.get("HTTP_REFERER"), 300)
            back_url = cache.get(f"{buss}-{check.id}-inventory_view_http_referer")

        inventory_data.delay(buss)
        data = cache.get(str(buss) + 'data')
        initial = cache.get(str(buss) + 'initial')
        current = cache.get(str(buss) + 'current')
        cat_count = cache.get(str(buss) + 'cat_count')
        available_prod = cache.get(str(buss) + 'available_prod')
        unavailable_prod = cache.get(str(buss) + 'unavailable_prod')
        prod_delta = cache.get(str(buss) + 'prod_delta')
        stock_value = cache.get(str(buss) + 'stock_value')
        stock_delta = cache.get(str(buss) + 'stock_delta')
        stock_count = cache.get(str(buss) + 'stock_count')
        current_percentage = cache.get(str(buss) + 'current_percentage')
        current_remainder = cache.get(str(buss) + 'current_remainder')

        if (not data and not initial and not current and not cat_count and not available_prod and
                not unavailable_prod and not prod_delta and not stock_value and not stock_delta and
                not stock_count and not current_percentage and not current_remainder):
            (data, initial, current, cat_count, available_prod, unavailable_prod, prod_delta,
             stock_value, stock_delta, stock_count, current_percentage, current_remainder) = inventory_data(buss)

        least_performing.delay(buss)
        prod_performance = cache.get(str(buss) + 'prod_performance')
        if not prod_performance:
            prod_performance = least_performing(buss)

        if not stock_value:
            stock_value = 0

        if request.method == 'POST':
            if 'save' in request.POST:
                name = request.POST.get('name')
                notes = request.POST.get('notes')

                try:
                    cat = InventoryCategory.objects.get(Business=check.Business, Name=name)
                    return HttpResponse(f"A category by the name : '{cat.Name}' already exists")
                except InventoryCategory.DoesNotExist:
                    cat = InventoryCategory(Business=check.Business, Name=name, Notes=notes)
                    cat.save()
                    return redirect('/inventory/')

            if 'delete' in request.POST:
                item = request.POST.get('delete')
                try:
                    item = InventoryProduct.objects.get(pk=item)
                    messages.warning(request, f'delete inventory {item.Name}')
                except InventoryProduct.DoesNotExist:
                    messages.error(request, 'unable to locate the item in memory')

            if 'confirm' in request.POST:
                item = request.POST.get('confirm')
                try:
                    InventoryProduct.objects.get(pk=item).delete()
                    messages.success(request, 'item deleted successfully')
                except InventoryProduct.DoesNotExist:
                    messages.error(request, 'unable to locate the item in memory')

            if 'show_this_product' in request.POST:
                product_id = request.POST.get('show_this_product')
                product_id = int(product_id)
                try:
                    product = InventoryProduct.objects.get(pk=product_id)
                    product_info = InventoryProductInfo.objects.get(Product__id=product.id)
                except InventoryProduct.DoesNotExist:
                    messages.error(request, 'failed to process inventory item')

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")
    context = {
        'data': data,
        'item': item,
        'initial': initial,
        'current': current,
        'cat_count': cat_count,
        'available_prod': available_prod,
        'unavailable_prod': unavailable_prod,
        'prod_delta': prod_delta,
        'stock_value': stock_value,
        'stock_count': stock_count,
        'stock_delta': stock_delta,
        'current_percentage': current_percentage,
        'prod_performance': prod_performance,
        'current_remainder': current_remainder,
        'product': product,
        'product_info': product_info,
        'back_url': back_url
    }
    return render(request, 'inventory.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def add_inventory(request, id=0):
    draft_count = 0
    initial = None
    draft_li = []
    buying_price = None
    expense = None
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        categories = InventoryCategory.objects.filter(Business=buss)
        if id != 0:
            try:
                initial = InventoryDraft.objects.get(Business=buss, pk=id)
                buying_price = round(initial.Cost/initial.InitialQuantity)
                expense = initial.Expenses

            except InventoryDraft.DoesNotExist:
                pass
        else:
            draft_li = InventoryDraft.objects.filter(Business=buss)

            if draft_li:
                draft_count = draft_li.count()
                initial = draft_li[0]
                buying_price = round(initial.Cost / initial.InitialQuantity)
                expense = initial.Expenses

        if request.method == 'POST':
            if 'save' in request.POST:
                """product"""
                category = request.POST.get('category')
                name = request.POST.get('name')
                brand = request.POST.get('brand')
                size = request.POST.get('size')
                expiry_date = request.POST.get('expiry_date')

                """product information"""
                location = request.POST.get('location')
                b_price = request.POST.get('BPrice')
                s_price = request.POST.get('SPrice')
                quantity = request.POST.get('quantity')
                code = request.POST.get('barcode')
                reorder = request.POST.get('reorder')

                if b_price:
                    b_price = int(b_price)
                else:
                    b_price = buying_price
                s_price = int(s_price)
                if quantity:
                    quantity = int(quantity)
                else:
                    quantity = initial.InitialQuantity
                if name:
                    pass
                else:
                    name = initial.Name
                if reorder:
                    reorder = int(reorder)

                total = s_price * quantity
                cost = b_price * quantity
                try:
                    category = InventoryCategory.objects.get(Business=buss, pk=category)

                except InventoryCategory.DoesNotExist():
                    return HttpResponse("Failed to process category information,"
                                        " please retry or contact developer if the problem persists")

                try:
                    InventoryProduct.objects.get(Business=buss, Expenses=expense, Category=category)
                    messages.error(request, "Error: an instance of this inventory item already exist")
                except InventoryProduct.DoesNotExist:
                    if expiry_date:
                        inv = InventoryProduct(Business=buss, Expenses=expense, Category=category,  Name=name,
                                               Brand=brand, Size=size, ExpiryDate=expiry_date)
                    else:
                        inv = InventoryProduct(Business=buss, Expenses=expense, Category=category, Name=name,
                                               Brand=brand, Size=size)
                    inv.save()

                    if not code:
                        code = category.Name[0:1] + name[0:1] + brand[0:1] + str(inv.id)

                    inv_info = InventoryProductInfo(Business=buss, Product=inv, Location=location, Cost=cost,
                                                    BPrice=b_price, SPrice=s_price, InitialQuantity=quantity,
                                                    CurrentQuantity=quantity, InitialValue=total, CurrentValue=total,
                                                    ReorderPerc=reorder, Code=code)
                    inv_info.save()
                    if initial:
                        initial.delete()
                    if draft_count > 1:
                        return redirect('/add_inventory/')
                    else:
                        return redirect('/inventory/')

            if 'this_draft' in request.POST:
                choice = request.POST.get("selected_draft")
                if choice:
                    choice = int(choice)
                    initial = InventoryDraft.objects.get(pk=choice)
                else:
                    messages.error(request, 'please select an item')

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")
    context = {
        'categories': categories,
        'draft_li': draft_li,
        'initial': initial,
        'draft_count': draft_count,
        'buying_price': buying_price,
    }
    return render(request, 'addInventory.html', context)
