from django.shortcuts import render, HttpResponse
from User.models import TaxSettings
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee, TaxYear
from calendar import monthrange
from datetime import datetime, timezone
from assets.models import Assets
from User.models import TaxYear
from income.service_income_history import get_tax_years
from .profitAndLoss import expenses, product_revenue, service_revenue, debt_total, totals_and_profits, pay_out
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from income.service_income_history import date_initial
from django.contrib import messages


def get_profit_and_loss_time_series(buss, tax_settings, assets,  start, end):

    today = datetime.now().date()
    time_series = {}
    total_annual_depreciation = 0

    tax_years, start_, end_ = get_tax_years(buss, start, end)
    for ty in tax_years:
        start_ = ty.TaxYearStart
        end_ = ty.TaxYearEnd

        (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
         total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

        # annual depreciation is recorded as expense that reduces net-income
        if assets.exists():
            for a in assets:
                if (a.Date.date - today) < (a.Date + relativedelta(years=a.UsefulLife)):
                    total_annual_depreciation += a.AnnualDepreciation

        total_expense += total_annual_depreciation

        paid_for += total_annual_depreciation

        product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax = \
            product_revenue(buss, tax_settings, start, end)

        service_income, total_service_income, total_service_vat, total_service_presumptive_tax = (
            service_revenue(buss, tax_settings, start, end))

        total_debt = debt_total(buss, start, end)

        (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
         net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand) = \
            totals_and_profits(buss, start, end, tax_settings, total_debt, total_service_vat, total_product_vat,
                               total_product_presumptive_tax, total_service_presumptive_tax, total_product_income,
                               total_service_income, cog, total_expense)

        total_dividends, retained_earnings = pay_out(buss, net_profit)

        time_series[f'{start_.date()} to {end_.date()}'] = {
            'product_income': product_income, 'total_product_income': total_product_income,
            'service_income': service_income, 'total_service_income': total_service_income, 'total_sales': total_sales,
            'total_vat': total_vat, 'total_presumptive_tax': total_presumptive_tax,
            'revenue_after_tax': revenue_after_tax, 'income_in_hand': income_in_hand, 'paid_for': paid_for,
            'oe': operational_expense, 'pe': payroll_expense, 'total_expense': total_expense,
            'oe_total': total_operational_expense, 'pe_total': total_payroll_expense,
            'total_annual_depreciation': total_annual_depreciation, 'total_discount': total_discount,
            'discounts': discounts, 'total_debt': total_debt, 'total_credit': total_credit, 'cog': cog, 'gp': gp,
            'op': op, 'net_profit': net_profit, 'income_tax': income_tax,
            'profit_after_income_tax': profit_after_income_tax, 'profit_perc': profit_perc
        }

    return time_series


def profit_and_loss_time_series(request):
    time_series = None
    focus_on = None
    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business.id

        tax_settings = TaxSettings.objects.get(Business__id=buss)
        assets = Assets.objects.filter(Business__id=buss)

        start = cache.get(f'{buss}_{user_object.id}_profit_and_loss_time_series_start')
        end = cache.get(f'{buss}_{user_object.id}_profit_and_loss_time_series_end')

        if start and end:
            time_series = get_profit_and_loss_time_series(buss, tax_settings, assets, start, end)
            start_initial = date_initial(start)
            end_initial = date_initial(end)
        else:
            all_years = TaxYear.objects.all()
            if all_years.exists():
                start = all_years[0].TaxYearStart
                end = all_years[len(all_years)-1].TaxYearEnd

                time_series = get_profit_and_loss_time_series(buss, tax_settings, assets, start, end)

        if request.method == 'POST':
            if 'filter' in request.POST:
                start = request.POST.get('start')
                end = request.POST.get('end')

                date_format = '%Y-%m-%d'
                start = datetime.strptime(start, date_format).replace(tzinfo=timezone.utc)
                end = datetime.strptime(end, date_format).replace(tzinfo=timezone.utc)

                cache.set(f'{buss}_{user_object.id}_profit_and_loss_time_series_start', start, 300)
                cache.set(f'{buss}_{user_object.id}_profit_and_loss_time_series_end', end, 300)

                time_series = get_profit_and_loss_time_series(buss, tax_settings, assets, start, end)

            if 'focus_on' in request.POST:
                key = request.POST.get('focus_on')

                focus_on = time_series[key]
            if 'close' in request.POST:
                key = None

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")
    context = {
        'time_series': time_series,
        'focus_on': focus_on
    }
    return render(request, 'profit_and_loss_time_series.html', context)
