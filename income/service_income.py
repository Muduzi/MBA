# Create your views here.
from django.shortcuts import render, redirect, HttpResponse
from .models import ServiceIncome, Service, Package, Category, PackageServices, ServiceBuffer
from .service_graphs import income_this_week, daily_total_this_week, cash_credit_this_week
from User.models import Employee, Business
from django.contrib import messages
from User.decorator import allowed_users, check_active_subscription
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.db.models import Sum, Q
from django.core.cache import cache
import pickle
# from django_redis.cache import RedisCache
from .setCustomer import service_credit_set, service_cash_set
from User.models import CashAccount


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def services(request):
    packages = {}
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        services_obj = Service.objects.filter(Business=buss)
        packages_obj = Package.objects.filter(Business=buss)
        categories_obj = Category.objects.filter(Business=buss)

        for p in packages_obj:
            count = PackageServices.objects.filter(Package=p.id).count()
            packages[p.id] = {}
            packages[p.id]['Name'] = p.Name
            packages[p.id]['Price'] = p.Price
            packages[p.id]['Count'] = count

        if request.method == 'POST':
            if 'createCategory' in request.POST:
                name = request.POST.get('categoryName')
                notes = request.POST.get('categoryNotes')
                try:
                    Category(Business=buss, Name=name, Notes=notes).save()
                    messages.success(request, f'{name} category saved successfully')
                except Exception as e:
                    messages.error(request, f'failed to save {name} category due to "{e}" error')

            if 'createService' in request.POST:
                name = request.POST.get('name')
                category = request.POST.get('category')
                charging_criteria = request.POST.get('chargingCriteria')
                price = request.POST.get('price')
                description = request.POST.get('description')

                try:
                    cat = Category.objects.get(pk=int(category))
                    try:
                        Service(Business=buss, Name=name, Category=cat, Description=description, Price=price,
                                ChargingCriteria=charging_criteria).save()
                        messages.success(request, "Service registered successfully")
                    except Exception as e:
                        messages.error(request, f"failed to register service due to '{e}' error")
                except Category.DoesNotExist:
                    messages.error(request, f"The Category does not exist, refresh the page and try again")

            if 'createPackage' in request.POST:
                name = request.POST.get('packageName')
                category = request.POST.get('category')
                choices = request.POST.getlist('choices')
                price = request.POST.get('price')

                try:
                    cat = Category.objects.get(pk=int(category))

                    try:
                        new_package = Package(Business=buss, Category=cat, Name=name, Price=price)
                        new_package.save()
                        messages.success(request, "Service registered successfully")

                        try:
                            for c in choices:
                                for s in services_obj:
                                    if c == s.Name:
                                        PackageServices(Package=new_package, Service=s).save()
                                        messages.success(request, "Package saved successfully")
                        except Exception as e:
                            messages.error(request, f"failed to due to '{e}' error")

                    except Exception as e:
                        messages.error(request, f"failed to register spackage due to '{e}' error")

                except Category.DoesNotExist:
                    messages.error(request, f"The Category does not exist, refresh the page and try again")

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'services': services_obj,
        'packages': packages,
        'categories': categories_obj
    }
    return render(request, 'services.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
# @check_active_subscription(allowed_subscriptions=['Basic', 'Standard', 'Advanced', 'Premium'])
def service_income(request):
    customer = None
    result = None
    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        table = income_this_week(buss)
        dates, amounts = daily_total_this_week(buss)
        cash, credit = cash_credit_this_week(buss)

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'table': table,
        'dates': dates,
        'amounts': amounts,
        'cash': cash,
        'credit': credit,
        'result': result,
    }
    return render(request, 'serviceIncome.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def service_sale(request):
    paid = 0
    excess = 0

    try:
        user_obj = request.user
        check = Employee.objects.get(User=user_obj.id)
        buss = check.Business

        buffer = ServiceBuffer.objects.filter(Business=buss.id, Cashier=user_obj)
        total = buffer.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        packages_obj = Package.objects.filter(Business=buss.id)
        services_obj = Service.objects.filter(Business=buss.id)

        if request.method == 'POST':
            if 'selectedServices' in request.POST:
                quantity = request.POST.get('quantity')
                choices = request.POST.getlist('services')
                choices_li = [int(num) for num in choices]

                if not quantity:
                    quantity = 1
                else:
                    quantity = int(quantity)

                si_type = 'services'
                result = buffer_service_service_income(buss, user_obj, packages_obj, services_obj, si_type, choices_li,
                                                       quantity)
                if result:
                    messages.error(request, f'{result}')

                return redirect('/service_sale/')

            if 'selectedPackages' in request.POST:
                quantity = request.POST.get('quantity')
                choices = request.POST.getlist('packages')

                choices_li = [int(num) for num in choices]

                if not quantity:
                    quantity = 1
                else:
                    quantity = int(quantity)

                si_type = 'packages'
                result = buffer_service_service_income(buss, user_obj, packages_obj, services_obj, si_type, choices_li,
                                                       quantity)
                if result:
                    messages.error(request, f'{result}')

                return redirect('/service_sale/')

            if 'finalise' in request.POST:
                paid = request.POST.get('amount')
                p_mode = request.POST.get('p_mode')
                attach_customer = request.POST.get('attach customer')

                for b in buffer:
                    b.PMode = p_mode
                    b.save()

                if attach_customer:
                    attach_customer = True
                else:
                    attach_customer = False

                if not paid:
                    paid = 0
                else:
                    paid = int(paid)

                if p_mode == 'Credit' or attach_customer == True:
                    return redirect(f"/set_customer/")
                else:
                    try:
                        if paid < total:
                            messages.error(request, f'insufficient funds, please add {excess} to the amount paid')

                        elif paid >= total:
                            excess = paid - total
                            result = service_cash_set(buss, user_obj, buffer)
                            if not 'success':
                                messages.error(request, f'{result}')

                    except Exception as e:
                        messages.error(request, f'{e}')

            if 'invoice' in request.POST:
                return redirect('/invoice_form/0/services/')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'buffer': buffer,
        'packages': packages_obj,
        'services': services_obj,
        'total': total,
        'paid': paid,
        'excess': excess,
    }
    return render(request, 'serviceSale.html', context)


def buffer_service_service_income(buss, user_obj, packages_obj, services_obj, si_type, choices_li, quantity):
    try:
        if si_type == 'services':
            for s in services_obj:
                for c in choices_li:
                    if s.id == c:
                        ServiceBuffer(Business=buss, Cashier=user_obj, Service=s, Quantity=quantity,
                                      Amount=s.Price*quantity).save()
        if si_type == 'packages':
            for p in packages_obj:
                for c in choices_li:
                    if p.id == c:
                        ServiceBuffer(Business=buss, Cashier=user_obj, Package=p, Quantity=quantity,
                                      Amount=p.Price*quantity).save()

    except Exception as e:
        return e


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def service(request, id=0):
    changes = []
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        data = Service.objects.get(Business=buss, pk=id)
        categories = Category.objects.filter(Business=buss)

        if request.method == 'POST':
            if 'saveChanges' in request.POST:
                name = request.POST.get('name')
                charging_criteria = request.POST.get('chargingCriteria')
                category = request.POST.get('category')
                price = request.POST.get('price')
                description = request.POST.get('description')

                if name:
                    if name != data.Name:
                        data.Name = name
                        changes.append(name)
                if charging_criteria:
                    if charging_criteria != data.ChargingCriteria:
                        data.ChargingCriteria = charging_criteria
                        changes.append(charging_criteria)
                if category:
                    category = Category.objects.get(Business=buss, pk=int(category))
                    if category != data.CatalogueCategory:
                        data.CatalogueCategory = category
                        changes.append(category)
                if price:
                    price = int(price)
                    if price != data.Price:
                        data.Price = price
                        changes.append(price)
                if description:
                    if description != data.Description:
                        data.Description = description
                        changes.append(description)
                data.save()
                if changes:
                    messages.success(request, f'Changes saved')
                else:
                    messages.info(request, 'No changes to save')
    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'data': data,
        'categories': categories
    }
    return render(request, 'service.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def package(request, id=0):
    changes = []
    services_obj = {}
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        data = cache.get('package'+str(id))
        if not data:
            try:
                data = Package.objects.get(Business=buss, pk=id)
                cache.set('package'+str(id), data, 5)
            except Package.DoesNotExist:
                return redirect('/services/')

        pack_services = cache.get('pack_serves'+str(data.id))
        if not pack_services:
            pack_services = PackageServices.objects.filter(Package=data)
            cache.set('pack_serves'+str(data.id), pack_services,  5)

        services = Service.objects.filter(Business=buss)
        if pack_services:
            for s in services:
                for p_s in pack_services:
                    if s != p_s.Service:
                        services_obj[s.id] = s
        else:
            for s in services:
                services_obj[s.id] = s

        categories = Category.objects.filter(Business=buss)

        if request.method == 'POST':
            if 'editPackage' in request.POST:
                name = request.POST.get('packageName')
                category = request.POST.get('category')
                price = request.POST.get('price')
                category = int(category)
                if name:
                    if name != data.Name:
                        data.Name = name
                        changes.append(name)

                if category:
                    if category != data.Category.id:
                        category = Category.objects.get(Business=buss, pk=category)
                        data.Category = category
                        changes.append(category)
                if price:
                    price = int(price)
                    if price != data.Price:
                        data.Price = price
                        changes.append(price)

                if changes:
                    data.save()
                    messages.success(request, f'Changes saved')
                else:
                    messages.info(request, 'No changes to save')

            if 'addService' in request.POST:
                choices = request.POST.getlist('choices')
                choices2 = [int(num) for num in choices]

                for c in choices2:
                    try:
                        service_obj = Service.objects.get(pk=c)
                        try:
                            PackageServices.objects.get(pk=service_obj.id)
                            choices2.remove(c)
                            print('already exists')
                        except PackageServices.DoesNotExist:
                            try:
                                for s in services_obj.values():
                                    if c == s.id:
                                        PackageServices(Package=data, Service=s).save()
                                        pack_services = PackageServices.objects.filter(Package=data)
                                        cache.set(data, pack_services, 5)

                                        messages.success(request, "service successfully added to the package")
                            except Exception as e:
                                messages.error(request, f"failed to due to '{e}' error")
                    except Service.DoesNotExist:
                        messages.error(request, f"failed to process the service, please try refreshing your page")
                pack_services = PackageServices.objects.filter(Package=data)
                cache.set(data, pack_services, 5)

            if 'remove' in request.POST:
                selected = request.POST.get('remove')

                try:
                    PackageServices.objects.get(pk=int(selected)).delete()
                    pack_services = PackageServices.objects.filter(Package=data)
                    cache.set(data, pack_services, 5)
                    messages.success(request, 'service removed successfully')
                except Exception as e:
                    print(e)
                    messages.error(request, 'failed to remove the service from the package')

            if 'delete' in request.POST:
                messages.warning(request, 'Press confirm to delete')
            if 'confirm' in request.POST:
                for p_s in pack_services:
                    p_s.delete()
                data.delete()
                return redirect('/services/')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'services_obj': services_obj,
        'data': data,
        'pack_services': pack_services,
        'categories': categories,
    }
    return render(request, 'package.html', context)

