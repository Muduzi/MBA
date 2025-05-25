# Create your views here.
from django.shortcuts import render, redirect, HttpResponse
from .models import ServiceIncome, ServiceBuffer, ProductIncome, IncomeBuffer
from inventory.models import InventoryProductInfo
from debts.models import Debt, Customer
from User.models import Employee, Business
from django.contrib import messages
from django.db.models import Sum, Q
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from User.models import CashAccount


def find_customer(buss, search_item):
    search_result = Customer.objects.filter(Business=buss, Name__contains=search_item)

    return search_result


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def set_customer(request, id=0):
    search_result = None
    items = None
    data_s = None
    data_p = None
    result = None
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        data_s = ServiceBuffer.objects.filter(Business=buss, Cashier=user_obj)
        if not data_s:
            data_p = IncomeBuffer.objects.filter(Business=buss, Cashier=user_obj)

            messages.error(request, 'Unable to process the transaction draft')

        customers = Customer.objects.filter(Business=buss)

        if request.method == 'POST':
            if 'newCustomer' in request.POST:
                name = request.POST.get('name')
                email = request.POST.get('email')
                contact = request.POST.get('contact')
                notes = request.POST.get('notes')

                try:
                    customer = Customer.objects.get(Business=buss, Name=name, Email=email)
                except Customer.DoesNotExist:
                    customer = Customer(Business=buss, Name=name, Email=email, Contact=contact, Notes=notes)
                    customer.save()

                if data_s:
                    if data_s[0].PMode == 'Credit':
                        result = service_credit_set(buss, user_obj, data_s, customer)

                    elif data_s[0].PMode == 'Cash':
                        result = service_cash_set(buss, user_obj, data_s, customer=None)

                elif data_p:
                    result = product_set(buss, user_obj, data_p, customer)

                if type(result) == int:
                    return redirect(f'/debt_form/{result}/')
                elif result == 'success':
                    messages.success(request, 'sales record made successfully')
                else:
                    messages.error(request, f"{result}")

            if 'search' in request.POST:
                search_item = request.POST.get('search')

                search_result = find_customer(buss, search_item)

                if not search_result:
                    messages.error(request, 'Customer profile not found; make sure you types the name correctly')

            if 'selectedCustomer' in request.POST:
                search_item = request.POST.get('search')
                customer = request.POST.get('customer')

                if search_item:
                    search_result = find_customer(buss, search_item)

                    if not search_result:
                        messages.error(request, 'Customer profile not found; make sure you types the name correctly')

                elif customer:
                    customer = int(customer)
                    for c in customers:
                        if c.id == customer:
                            if data_s:
                                if data_s[0].PMode == 'Credit':
                                    result = service_credit_set(buss, user_obj, data_s, c)

                                elif data_s[0].PMode == 'Cash':
                                    result = service_cash_set(buss, user_obj, data_s, c)

                            elif data_p:
                                result = product_set(buss, user_obj, data_p, c)

                            if type(result) == int:
                                return redirect(f'/debt_form/{result}/')
                            if result == 'success':
                                messages.success(request, 'sales record made successfully')
                            else:
                                messages.error(request, f"{result}")
    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'data_s': data_s,
        'data_p': data_p,
        'customers': customers,
        'search_result': search_result
    }
    return render(request, 'income/setCustomer.html', context)


def service_credit_set(buss, user_obj, data, customer=None):
    total = data.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    try:
        debt = Debt(Business=buss, Customer=customer, Amount=total, Status='Not Paid', Received=0,
                    Notes=customer.Notes)
        debt.save()
        for i in data:
            if i.Package:
                ServiceIncome(Business=buss, Cashier=user_obj, Package=i.Package, Quantity=i.Quantity,
                              Amount=i.Amount, Customer=customer, Debt=debt, PMode=i.PMode).save()
            elif i.Service:
                ServiceIncome(Business=buss, Cashier=user_obj, Service=i.Service, Quantity=i.Quantity,
                              Amount=i.Amount, Customer=customer, Debt=debt, PMode=i.PMode).save()
        data.delete()

        return debt.id
    except Exception as e:
        return e


def service_cash_set(buss, user_obj, data, customer=None):
    discount = False
    cash_account = CashAccount.objects.get(Business=buss)
    try:
        for i in data:
            if i.Package:
                if (i.Package.Price*i.Quantity) > i.Amount:
                    discount = True
                ServiceIncome(Business=buss, Cashier=user_obj, Customer=customer, Package=i.Package,
                              Quantity=i.Quantity, Amount=i.Amount, PMode='Cash', Discount=discount).save()
                cash_account.Value += i.Amount

            elif i.Service:
                if (i.Service.Price*i.Quantity) > i.Amount:
                    discount = True
                ServiceIncome(Business=buss, Cashier=user_obj, Customer=customer, Service=i.Service,
                              Quantity=i.Quantity, Amount=i.Amount, PMode='Cash', Discount=discount).save()
                cash_account.Value += i.Amount

            cash_account.save()
        data.delete()
        # if successfully recorded
        return 'success'
    except Exception as e:
        return e


def product_set(buss, user_obj, data_p, customer):
    total = data_p.aggregate(Sum('Amount'))
    total = total['Amount__sum']
    if not total:
        total = 0

    try:
        debt = Debt(Business=buss, Customer=customer, Amount=total, Status='Not Paid', Received=0,
                    Notes=customer.Notes)
        debt.save()

        discount = False
        for i in data_p:
            prod_info = InventoryProductInfo.objects.get(Business=buss, Code=i.Code)
            if (prod_info.BPrice*i.Quantity) > i.Amount:
                discount = True
            prod_info.CurrentQuantity -= i.Quantity
            prod_info.CurrentValue -= i.Amount

            ProductIncome(Business=buss, Cashier=user_obj, Debt=debt, Code=prod_info.Code, Product=i.Product,
                          Amount=i.Amount, Quantity=i.Quantity, PMode='Credit', Discount=discount).save()

        data_p.delete()

        return debt.id
    except Exception as e:
        return e
