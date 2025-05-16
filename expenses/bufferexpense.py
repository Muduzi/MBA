from django.shortcuts import render, redirect, HttpResponse
from django.db.models import Sum, Q
from expenses.models import BufferExpense
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
# Create your views here.


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def buffer_expense_view(request):
    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business

        data = BufferExpense.objects.filter(Business=buss)
        total = data.aggregate(Sum('Price'))
        total = total['Price__sum']
        if not total:
            total = 0

        if request.method == 'POST':
            if 'save' in request.POST:
                name = request.POST.get('name')
                quantity = request.POST.get('quantity')
                price = request.POST.get('price')
                notes = request.POST.get('notes')
                b = BufferExpense(Business=buss, Cashier=user_object, Name=name, Quantity=quantity, Price=price,
                                  Notes=notes)
                b.save()
                return redirect('/buffer_expense/')

            if 'finalise' in request.POST:
                p_mode = request.POST.get('PMode')
                e_type = request.POST.get('type')
                for d in data:
                    d.PMode = p_mode
                    d.Name = e_type
                    d.save()
                if data.exists():
                    return redirect('/set_supplier/')
                else:
                    messages.error(request, 'Input data required for the transaction')

            if 'refresh' in request.POST:
                if data:
                    for d in data:
                        d.delete()
                    return redirect('/buffer_expense/')

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer"
                            "if the problem persists")

    context = {
        "data": data,
        'total': total,
    }
    return render(request, 'expense/bufferExpense.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def edit_buffer_expense(request, id=0):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        try:
            data = BufferExpense.objects.get(Business=buss, pk=id)

            if request.method == 'POST':
                if 'save' in request.POST:
                    name = request.POST.get('name')
                    price = request.POST.get('price')
                    e_type = request.POST.get('type')
                    quantity = request.POST.get('quantity')
                    notes = request.POST.get('notes')
                    price = int(price)
                    quantity = int(quantity)

                    if name:
                        if data.Name != name:
                            data.Name = name
                    if price:
                        if data.Price != price:
                            data.Price = price
                    if e_type:
                        if data.Name != e_type:
                            data.Name = e_type
                    if quantity:
                        if data.Quantity != quantity:
                            data.Quantity = quantity
                    if notes:
                        if data.Notes != notes:
                            data.Notes = notes
                    data.save()

                    return redirect('/buffer_expense/')

                elif 'delete' in request.POST:
                    data.delete()
                    return redirect('/buffer_expense/')

        except BufferExpense.DoesNotExist:
            return HttpResponse("The item you are trying to access doesn't seem to exist")

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer"
                            "if the problem persists")
    context = {
        'data': data
    }
    return render(request, 'expense/editBufferExpense.html', context)
