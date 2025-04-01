from django.shortcuts import render, redirect, HttpResponse
from _datetime import datetime, timedelta
from .models import InventoryCategory, InventoryProduct, InventoryProductInfo, InventoryDraft
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from User.models import Employee
from expenses.models import Expense
from credits.models import Credit
from User.models import CashAccount
from django.contrib import messages


# Create your views here
@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def replenish(request, id=0):
    delta = timedelta(days=7)
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        cap = CashAccount.objects.get(Business=buss)
        product = InventoryProduct.objects.get(Business=buss, pk=id)
        product_info = InventoryProductInfo.objects.get(Business=buss, Product=product)
        categories = InventoryCategory.objects.filter(Business=buss)
        if product.ExpiryDate:
            if len(str(product.ExpiryDate.day)) == 1:
                day = f'0{product.ExpiryDate.day}'
            else:
                day = product.ExpiryDate.day
            if len(str(product.ExpiryDate.month)) == 1:
                month = f'0{product.ExpiryDate.month}'
            else:
                month = product.ExpiryDate.month

            date = f"{product.ExpiryDate.year}-{month}-{day}"
        else:
            date = None

        if request.method == 'POST':
            if 'save' in request.POST:
                """product"""
                name = request.POST.get('name')
                brand = request.POST.get('brand')
                size = request.POST.get('size')
                expiry_date = request.POST.get('expiry_date')
                """product information"""
                location = request.POST.get('location')
                b_price = request.POST.get('b_price')
                s_price = request.POST.get('s_price')
                quantity = request.POST.get('quantity')
                reorder = request.POST.get('reorder')
                code = request.POST.get('barcode')
                p_mode = request.POST.get('p_mode')
                if expiry_date:
                    expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()

                b_price = int(b_price)
                s_price = int(s_price)
                quantity = int(quantity)
                reorder = int(reorder)

                total = s_price * quantity
                cost = b_price * quantity

                description = f"restocking inventory item:'{product.Name}' on '{datetime.now()}'"

                if p_mode == 'Cash' and cap.Capital >= cost:
                    expense = Expense(Business=buss, Supplier=product.Expenses.Supplier, Cashier=user_obj,
                                      Name=product.Name, Price=cost, Quantity=quantity, Type='Stock', PMode='Credit',
                                      Notes=description)
                    expense.save()
                    cap.Capital -= cost
                    cap.save()
                else:
                    cred = Credit(Date=datetime.now(), Business=buss, Supplier=product.Expenses.Supplier, Amount=total,
                                  Due=datetime.now() + delta)
                    cred.save()
                    expense = Expense(Business=buss, Supplier=product.Expenses.Supplier, Credit=cred,
                                      Cashier=user_obj, Name=product.Name, Price=cost, Quantity=quantity,
                                      Type='Stock', PMode='Credit', Notes=description)
                    expense.save()
                if not product.ExpiryDate:
                    if product_info.BPrice == b_price and product_info.Code == code:
                        product_info.InitialQuantity += quantity
                        product_info.CurrentQuantity += quantity
                        product_info.InitialValue += total
                        product_info.CurrentValue += total
                        product_info.save()
                    else:
                        batch = len(InventoryProduct.objects.filter(Q(Business=buss), Q(Name__contains=product.Name) &
                                                                 Q(Brand__contains=product.Brand) &
                                                                 Q(Size__contains=product.Size)))+1
                        batch = str(batch)
                        inv = InventoryProduct(Business=buss, Expenses=expense, Category=product.CatalogueCategory,
                                               Name=product.Name+batch, Brand=product.Brand, Size=product.Size)
                        inv.save()

                        if not code:
                            code = product.CatalogueCategory.Name[0:1] + product.Name[0:1] + product.Brand[0:1] + str(inv.id)

                        inv_info = InventoryProductInfo(Business=buss, Product=inv, Location=location, Cost=cost,
                                                        BPrice=b_price, SPrice=s_price, InitialQuantity=quantity,
                                                        CurrentQuantity=quantity, InitialValue=total,
                                                        CurrentValue=total,
                                                        ReorderPerc=reorder, Code=code)
                        inv_info.save()
                else:
                    if expiry_date == product.ExpiryDate.Date() and product_info.BPrice == b_price and product_info.Code == code:
                        product_info.InitialQuantity += quantity
                        product_info.CurrentQuantity += quantity
                        product_info.InitialValue += total
                        product_info.CurrentValue += total
                        product_info.save()
                    else:
                        batch = len(InventoryProduct.objects.filter(Q(Business=buss), Q(Name__contains=product.Name) &
                                                                 Q(Brand__contains=product.Brand) &
                                                                 Q(Size__contains=product.Size)))+1
                        batch = str(batch)
                        if expiry_date:
                            inv = InventoryProduct(Business=buss, Expenses=expense, Category=product.CatalogueCategory,
                                                   Name=(product.Name+batch), Brand=product.Brand, Size=product.Size,
                                                   ExpiryDate=expiry_date)

                            inv.save()
                        else:
                            inv = InventoryProduct(Business=buss, Expenses=expense, Category=product.CatalogueCategory,
                                                   Name=product.Name, Brand=product.Brand, Size=product.Size)
                            inv.save()

                        if not code:
                            code = product.CatalogueCategory.Name[0:1] + product.Name[0:1] + product.Brand[0:1] + str(inv.id)

                        inv_info = InventoryProductInfo(Business=buss, Product=inv, Location=location, Cost=cost,
                                                        BPrice=b_price, SPrice=s_price, InitialQuantity=quantity,
                                                        CurrentQuantity=quantity, InitialValue=total, CurrentValue=total,
                                                        ReorderPerc=reorder, Code=code)
                        inv_info.save()

                if expense.Credit and p_mode == 'Cash':
                    messages.success(request, "replenishing on credit successful; funds were insufficient.")
                if expense.Credit and p_mode == 'Credit':
                    return redirect(f'/credit_form/{expense.Credit.id}/')
                elif not expense.Credit:
                    messages.success(request, "replenishing on Cash successful")
    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")

    context = {
        'categories': categories,
        'product': product,
        'product_info': product_info,
        'date': date
    }
    return render(request, 'replenish.html', context)
