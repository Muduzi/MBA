from django.shortcuts import render, redirect, HttpResponse
from .models import *
from django.db.models import Sum, Q
from User.models import Employee, TaxSettings
from User.decorator import allowed_users
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.contrib import messages
from xhtml2pdf import pisa
from debts.models import Customer
from datetime import timezone, datetime
from inventory.models import InventoryProductInfo


def get_invoices(buss):
    today = datetime.now(timezone.utc).date()
    items_count = 0

    pending_invoices = Invoice.objects.filter(Business__id=buss, Status=False, ValidityLimit__gte=today)
    for i in pending_invoices:
        items = InvoiceItems.objects.filter(invoice=i)
        if items:
            items_count += int(items.count())

    total = pending_invoices.aggregate(Sum('GrandTotal'))
    total = total['GrandTotal__sum']
    if not total:
        total = 0

    total_vat = pending_invoices.aggregate(Sum('VAT'))
    total_vat = total_vat['VAT__sum']
    if not total_vat:
        total_vat = 0

    pending_invoices_stats = {'total': total, 'total_vat': total_vat,
                              'count': pending_invoices.count(), 'items': items_count}

    overdue_invoices = Invoice.objects.filter(Business__id=buss, Status=False, ValidityLimit__lt=today)
    for i in overdue_invoices:
        items = InvoiceItems.objects.filter(invoice=i)
        if items:
            items_count += int(items.count())

    total = overdue_invoices.aggregate(Sum('GrandTotal'))
    total = total['GrandTotal__sum']
    if not total:
        total = 0

    total_vat = overdue_invoices.aggregate(Sum('VAT'))
    total_vat = total_vat['VAT__sum']
    if not total_vat:
        total_vat = 0

    overdue_invoices_stats = {'total': total, 'total_vat': total_vat,
                              'count': overdue_invoices.count(), 'items':  items_count}

    processed_invoices = Invoice.objects.filter(Business__id=buss, Status=True)
    for i in processed_invoices:
        items = InvoiceItems.objects.filter(invoice=i)
        if items:
            items_count += int(items.count())
    total = processed_invoices.aggregate(Sum('GrandTotal'))
    total = total['GrandTotal__sum']
    if not total:
        total = 0

    total_vat = processed_invoices.aggregate(Sum('VAT'))
    total_vat = total_vat['VAT__sum']
    if not total_vat:
        total_vat = 0

    processed_invoices_stats = { 'total': total, 'total_vat':  total_vat,
                                 'count': processed_invoices.count(), 'items': items_count}

    return (pending_invoices, pending_invoices_stats, processed_invoices, processed_invoices_stats, overdue_invoices,
            overdue_invoices_stats)


def create_product_sale(user, invoice_id):
    try:
        user = User.objects.get(pk=user)
        invoice = Invoice.objects.get(pk=invoice_id)
        items = InvoiceItems.objects.filter(invoice__id=invoice.id)

        if items[0].Product:
            buffer = IncomeBuffer.objects.filter(Business=invoice.Business, Cashier=user)
            if buffer:
                buffer.delete()

            for i in items:
                ipi = InventoryProductInfo.objects.get(Product=i.Product)
                IncomeBuffer(Business=invoice.Business, Cashier=user, Product=i.Product, Code=ipi.Code,
                             Quantity=i.Quantity, Amount=i.Total).save()

            invoice.Status = True
            invoice.save()
            return 'products'

        elif items[0].Package or items[0].Service:
            buffer = ServiceBuffer.objects.filter(Business=invoice.Business, Cashier=user)
            if buffer:
                buffer.delete()

            for i in items:
                if i.Service:
                    ServiceBuffer(Business=invoice.Business, Cashier=user, Service=i.Service, Quantity=i.Quantity,
                                  Amount=i.Total).save()
                elif i.Package:
                    ServiceBuffer(Business=invoice.Business, Cashier=user, Package=i.Package, Quantity=i.Quantity,
                                  Amount=i.Total).save()

            invoice.Status = True
            invoice.save()
            return 'services'

    except Exception as e:
        return e


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def invoices_view(request):
    invoice_id = 0
    process_this_invoice = 0
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        (pending_invoices, pending_invoices_stats, processed_invoices, processed_invoices_stats, overdue_invoices,
         overdue_invoices_stats) = get_invoices(buss.id)

        if request.method == 'POST':
            if 'process_invoice' in request.POST:
                invoice_id = request.POST.get('process_invoice')
                process_this_invoice = int(invoice_id)

            if 'confirm_process_invoice' in request.POST:
                invoice_id = request.POST.get('confirm_process_invoice')
                invoice_id = int(invoice_id)

                result = create_product_sale(request.user.id, invoice_id)
                if result == 'products':
                    return redirect('/product_sale/')
                elif result == 'services':
                    return redirect('/service_sale/')
                else:
                    messages.error(request, f'{result}')

            if 'delete_invoice' in request.POST:
                invoice_id = request.POST.get('delete_invoice')
                invoice_id = int(invoice_id)

                messages.warning(request, 'Are you sure you want to delete this invoice ?')
            if 'confirm_delete' in request.POST:
                invoice_id = request.POST.get('confirm_delete')
                invoice_id = int(invoice_id)

                try:
                    Invoice.objects.get(pk=invoice_id).delete()

                    (pending_invoices, pending_invoices_stats, processed_invoices, processed_invoices_stats,
                     overdue_invoices, overdue_invoices_stats) = get_invoices(buss.id)

                    messages.success(request, 'Invoice deleted successfully')
                except Exception as e:
                    messages.error(request, f'failed to delete invoice; {e}')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'invoice_id': invoice_id,
        'process_this_invoice': process_this_invoice,
        'pending_invoices': pending_invoices,
        'pending_invoices_stats': pending_invoices_stats,
        'processed_invoices': processed_invoices,
        'processed_invoices_stats': processed_invoices_stats,
        'overdue_invoices': overdue_invoices,
        'overdue_invoices_stats': overdue_invoices_stats

    }
    return render(request, 'invoices.html', context)


def get_invoice(buss, id):
    try:
        invoice_obj = Invoice.objects.get(Business__id=buss, pk=id)

        tax_settings = TaxSettings.objects.get(Business__id=buss)

        invoice_items = InvoiceItems.objects.filter(invoice=invoice_obj)
        grand_total = invoice_items.aggregate(Sum('Total'))
        grand_total = grand_total['Total__sum']
        if not grand_total:
            grand_total = 0

        if invoice_obj.GrandTotal != grand_total:
            invoice_obj.GrandTotal = grand_total

            if tax_settings.IncludeVAT and tax_settings.ShowEstimates:
                try:
                    vat = (grand_total * tax_settings.VATRate) / 100
                    vat = round(vat)
                except ZeroDivisionError:
                    vat = 0
            else:
                vat = 0

            calculated_sub_total = int(grand_total-vat)

            if invoice_obj.SubTotal != calculated_sub_total:
                invoice_obj.SubTotal = calculated_sub_total

                invoice_obj.VAT = vat

            invoice_obj.save()
    except Invoice.DoesNotExist:
        invoice_obj = None
        invoice_items = None

    return invoice_obj, invoice_items


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def invoice_view(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        invoice_obj, invoice_items = get_invoice(buss.id, id)

        if request.method == 'POST':
            if 'generate' in request.POST:
                return redirect(f'/invoice_pdf/{invoice_obj.id}/')

            if 'process_invoice' in request.POST:
                result = create_product_sale(request.user.id, invoice_obj.id)
                if result == 'success':
                    return redirect('/product_sale/')
                else:
                    messages.error(request, f'{result}')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'buss': buss,
        'invoice_obj': invoice_obj,
        'invoice_items': invoice_items
    }
    return render(request, 'invoice.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def generate_invoice_pdf(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        template = get_template('generateInvoicePDF.html')

        try:
            inv_obj = Invoice.objects.get(pk=id)
            items = InvoiceItems.objects.filter(invoice=inv_obj.id)
        except Invoice.DoesNotExist:
            return redirect('/buffer/')
        context = {
            'buss': buss,
            'inv_obj': inv_obj,
            'items': items,

        }
        customer = 'Derrick Muduzi'
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Desposition'] = f'attachment;  filename="{customer}"'

        pisa.CreatePDF(html, dest=response)

        return response
    except Employee.DoesNotExist:
        return redirect("/login/")


def calculate_vat(buss, grand_total):
    tax_settings = TaxSettings.objects.get(Business=buss)

    if tax_settings.IncludeVAT and tax_settings.VATRate:
        try:
            vat = (grand_total * tax_settings.VATRate) / 100
            vat = round(vat)
        except ZeroDivisionError:
            vat = 0
    else:
        vat = 0

    return vat


def precess_product_invoice_items(items, buss):
    grand_total = items.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    vat = calculate_vat(buss, grand_total)

    sub_total = round(grand_total-vat)

    return grand_total, sub_total, vat


def precess_service_invoice_items(items, buss):
    grand_total = items.aggregate(Sum('Amount'))
    grand_total = grand_total['Amount__sum']
    if not grand_total:
        grand_total = 0

    vat = calculate_vat(buss, grand_total)

    sub_total = round(grand_total-vat)

    return grand_total, sub_total, vat


def date_initial(date_obj):
    if len(str(date_obj.day)) == 1:
        day = f'0{date_obj.day}'
    else:
        day = date_obj.day

    if len(str(date_obj.month)) == 1:
        month = f'0{date_obj.month}'
    else:
        month = date_obj.month

    date = f"{date_obj.year}-{month}-{day}"

    return date


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def invoice_form(request, id=0, choice=''):
    new_invoice = None
    dispatch_date = None
    validity_limit = None
    product_buffer = None
    service_buffer = None
    grand_total = 0
    sub_total = 0
    vat = 0

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        if choice == 'products':
            product_buffer = IncomeBuffer.objects.filter(Cashier=request.user)

            grand_total, sub_total, vat = precess_product_invoice_items(product_buffer, buss)

        if choice == 'services':
            service_buffer = ServiceBuffer.objects.filter(Cashier=request.user)

            grand_total, sub_total, vat = precess_service_invoice_items(service_buffer, buss)

        if id != 0:
            try:
                new_invoice = Invoice.objects.get(pk=id)

                dispatch_date = date_initial(new_invoice.DispatchDate)

                validity_limit = date_initial(new_invoice.DispatchDate)

            except Invoice.DoesNotExist:
                return redirect('/invoice_form')

        if request.method == 'POST':
            if 'finish invoice' in request.POST:
                order_number = request.POST.get('order_number')
                validity_limit = request.POST.get('validity_limit')
                dispatch_date = request.POST.get('dispatch_date')
                name = request.POST.get('name')
                email = request.POST.get('email')
                contact = request.POST.get('contact')
                notes = request.POST.get('notes')

                try:
                    customer = Customer.objects.get(Business=buss, Name=name, Email=email)
                except Customer.DoesNotExist:
                    customer = Customer(Business=buss, Name=name, Email=email, Contact=contact, Notes=notes)
                    customer.save()

                order_number = int(order_number)

                if new_invoice:
                    if order_number:
                        new_invoice.OrderNumber = order_number
                    new_invoice.DispatchDate = dispatch_date
                    if validity_limit:
                        new_invoice.ValidityLimit = validity_limit
                    if grand_total:
                        new_invoice.GrandTotal = grand_total
                    if vat:
                        new_invoice.VAT = vat
                    if sub_total:
                        new_invoice.SubTotal = sub_total
                    new_invoice.save()

                    if notes:
                        if notes != customer.Notes:
                            customer.Notes = notes
                            customer.save()

                    return redirect(f'/invoice_form/{new_invoice.id}/')

                else:
                    if dispatch_date:
                        new_invoice = Invoice(Business=buss, Cashier=request.user, Receiver=customer,
                                              OrderNumber=order_number, DispatchDate=dispatch_date,
                                              ValidityLimit=validity_limit, GrandTotal=grand_total, VAT=vat,
                                              SubTotal=sub_total, )

                    else:
                        new_invoice = Invoice(Business=buss, Cashier=request.user, Receiver=customer,
                                              GrandTotal=grand_total, VAT=vat, SubTotal=sub_total)
                    new_invoice.save()

                    if product_buffer:
                        for i in product_buffer:
                            try:
                                product_info = InventoryProductInfo.objects.get(Product=i.Product)
                                InvoiceItems(invoice=new_invoice, Product=i.Product, UnitPrice=product_info.SPrice,
                                             Total=i.Quantity * product_info.SPrice, Quantity=i.Quantity).save()
                            except InventoryProductInfo.DoesNotExist:
                                messages.error(request, 'problem processing {p.Product.Name} information')

                        product_buffer.delete()

                    elif service_buffer:
                        for i in service_buffer:
                            if i.Service:
                                InvoiceItems(invoice=new_invoice, Service=i.Service, UnitPrice=(i.Amount/i.Quantity),
                                             Total=i.Amount, Quantity=i.Quantity).save()

                            if i.Package:
                                InvoiceItems(invoice=new_invoice, Package=i.Package, UnitPrice=(i.Amount/i.Quantity),
                                             Total=i.Amount, Quantity=i.Quantity).save()

                        service_buffer.delete()

                    return redirect(f'/invoice/{new_invoice.id}/')

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'buss': buss,
        'gt': grand_total,
        'st': sub_total,
        'vat': vat,
        'new_invoice': new_invoice,
        'dispatch_date': dispatch_date,
        'validity_limit': validity_limit
    }
    return render(request, 'invoice_form.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def delivery_note(request):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        template = get_template('delivery_note.html')
        items = IncomeBuffer.objects.all()

        context = {
            'buss': buss,
            'items': items
        }
        customer = 'Derrick Muduzi'
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Desposition'] = f'attachment; filename="{customer}"'
        pisa.CreatePDF(html, dest=response)

        return response
    except Employee.DoesNotExist:
        return redirect("/login/")
