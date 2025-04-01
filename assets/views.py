import time

from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Assets, AssetSpecification, AssetPhotos
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from User.decorator import allowed_users
from User.models import Employee
from statements.ProfitAndLoss import get_tax_year

# Create your views here.


# Straight-line depreciation method
def annual_depreciation_calculater(initial_value, salvage_value, useful_life):
    depreciation_amount = initial_value - salvage_value
    annual_depreciation = depreciation_amount/useful_life
    depreciation_rate = (annual_depreciation/depreciation_amount) * 100

    return depreciation_amount, annual_depreciation, depreciation_rate


def accumulated_depreciation_calculater(a, tax_year):
    try:
        time_elapsed = (tax_year.TaxYearStart.date() - a.TaxYear.TaxYearStart.date()).days / 365

    except Exception as e:
        print(f'{e}')
        time_elapsed = 0

    if time_elapsed > 1:
        assets_current_value = a.InitialValue - (a.AnnualDepreciation * time_elapsed)
        if a.CurrentValue != assets_current_value:
            a.CurrentValue = assets_current_value
            a.save()

    accumulated_depreciation = a.AnnualDepreciation * time_elapsed
    return accumulated_depreciation, time_elapsed


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)', 'Business(Worker)'])
def assets_view(request):
    total_accumulated_depreciation = 0
    total_time_elapsed = 0
    total_useful_life = 0
    spent_useful_life = 0
    remaining_useful_life_perc = 0
    total_annual_depreciation = 0
    current_value = 0
    count = 0
    assets = {}
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        tax_year = get_tax_year(buss)

        assets_ = Assets.objects.filter(Business=buss).order_by('-id')
        current_value = assets_.aggregate(Sum('CurrentValue'))
        current_value = current_value['CurrentValue__sum']

        initial_value = assets_.aggregate(Sum('CurrentValue'))
        initial_value = initial_value['CurrentValue__sum']

        if assets_:
            count = assets_.count()
        if not current_value:
            current_value = 0
        if not initial_value:
            initial_value = 0

        for a in assets_:
            total_annual_depreciation += a.AnnualDepreciation
            total_useful_life += a.UsefulLife

            accumulated_depreciation, time_elapsed = accumulated_depreciation_calculater(a, tax_year)
            total_time_elapsed += time_elapsed
            total_accumulated_depreciation += accumulated_depreciation

            assets[a.id] = {}
            assets[a.id]['Date'] = a.Date
            assets[a.id]['Name'] = a.Name
            assets[a.id]['InitialValue'] = a.InitialValue
            assets[a.id]['DepreciationRate'] = a.DepreciationRate
            assets[a.id]['AccumulatedDepreciation'] = accumulated_depreciation
            assets[a.id]['CurrentValue'] = a.CurrentValue

        remaining_useful_life = total_useful_life - total_time_elapsed
        try:
            remaining_useful_life_perc = (remaining_useful_life / total_useful_life) * 100
        except ZeroDivisionError:
            remaining_useful_life_perc = 0

    except Employee.DoesNotExist:
        return HttpResponse('Failed to process your profile please retry or contact developer if the problem persists')

    context = {
        'assets': assets,
        'count': count,
        'current_value': current_value,
        'initial_value': initial_value,
        'spent_useful_life': spent_useful_life,
        'remaining_useful_life': remaining_useful_life,
        'remaining_useful_life_perc': remaining_useful_life_perc,
        'total_accumulated_depreciation': total_accumulated_depreciation,
        'total_annual_depreciation': total_annual_depreciation,
    }
    return render(request, 'Assets.html', context)


def get_form_input(request):
    name = request.POST.get('name')
    initial_value = request.POST.get('initial_value')
    useful_life = request.POST.get('useful_life')
    salvage_value = request.POST.get('salvage_value')
    notes = request.POST.get('notes')
    photos_li = request.FILES.getlist('photo')

    print('notes:', notes)
    if initial_value:
        initial_value = int(initial_value)
    if salvage_value:
        salvage_value = int(salvage_value)
    if useful_life:
        useful_life = int(useful_life)

    return name, initial_value, useful_life, salvage_value, notes, photos_li


def asset_form(request, id=0):
    asset = None
    specifications = None
    photos = None
    change = 0
    view_image = None
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        tax_year = get_tax_year(buss)
        try:
            asset = Assets.objects.get(Business=buss, pk=id)
            specifications = AssetSpecification.objects.filter(Asset=asset)
            photos = AssetPhotos.objects.filter(Asset=asset)

            if request.method == 'POST':
                if 'asset' in request.POST:
                    print('working')
                    name, initial_value, useful_life, salvage_value, notes, photos_li = get_form_input(request)
                    if name:
                        if asset.Name != name:
                            asset.Name = name
                            change += 1

                    if photos_li:
                        for p in photos_li:
                            AssetPhotos(Asset=asset, Photo=p).save()
                            change += 1
                    if notes:
                        if asset.Notes != notes:
                            asset.Notes = notes
                            asset.save()
                            change += 1

                    if change:
                        asset.save()
                        if change == 1:
                            messages.success(request, 'change saved successfully')
                        elif change > 1:
                            messages.success(request, 'changes saved successfully')
                    return redirect(f'/asset_form/{asset.id}/')

                if 'asset_specification' in request.POST:
                    title = request.POST.get('title')
                    description = request.POST.get('description')
                    print('working')
                    try:
                        AssetSpecification(Asset=asset, Title=title, Description=description).save()
                        print('working2')
                        specifications = AssetSpecification.objects.filter(Asset=asset)
                        print('working3')
                    except Exception as e:
                        messages.error(request, f'{e}')

                if 'view_image' in request.POST:
                    image_id = request.POST.get('view_image')
                    image_id = int(image_id)

                    for p in photos:
                        if p.id == image_id:
                            view_image = p

                if 'delete' in request.POST:
                    image_id = request.POST.get('delete')
                    image_id = int(image_id)

                    for p in photos:
                        if p.id == image_id:
                            p.delete()
                            view_image = None
                            messages.success(request, 'image delete successfully')

        except Assets.DoesNotExist:
            if request.method == 'POST':
                if 'asset' in request.POST:
                    name, initial_value, useful_life, salvage_value, notes, photos = get_form_input(request)
                    depreciation_amount, annual_depreciation, depreciation_rate = (
                        annual_depreciation_calculater(initial_value, salvage_value, useful_life))

                    try:
                        asset = Assets(Business=buss, TaxYear=tax_year, Name=name, InitialValue=initial_value,
                                       CurrentValue=initial_value, DepreciationRate=depreciation_rate,
                                       AnnualDepreciation=annual_depreciation, SalvageValue=salvage_value,
                                       UsefulLife=useful_life, Notes=notes)
                        asset.save()

                        messages.success(request, f'asset listed successfully')
                        time.sleep(10)
                        return redirect(f'/asset_form/{asset.id}/')
                    except Exception as e:
                        messages.error(request, f'{e}')

    except Employee.DoesNotExist:
        messages.error(request, 'failed to process your profile')

    context = {
        'asset': asset,
        'specifications': specifications,
        'photos': photos,
        'view_image': view_image,
    }
    return render(request, 'AssetForm.html', context)



