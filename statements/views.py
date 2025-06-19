from django.shortcuts import render, HttpResponse
from datetime import datetime, timezone
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee, TaxSettings
from .profitAndLoss import (expenses, product_revenue, service_revenue, debt_total,
                            totals_and_profits)
from assets.models import Assets
from django.core.cache import cache


# for the filter statement
@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def profit_and_loss_dash_range(request):
    product_income = {}
    cog = 0
    gp = 0
    op = 0
    discounts = {}
    income_in_hand = 0
    net_profit = 0
    profit_perc = 0
    total_sales = 0
    revenue_after_tax = 0
    total_presumptive_tax = 0
    total_product_income = 0
    service_income = {}
    total_service_income = 0
    paid_for = 0
    operational_expense = 0
    payroll_expense = 0
    total_expense = 0
    total_operational_expense = 0
    total_payroll_expense = 0
    total_debt = 0
    total_credit = 0
    total_vat = 0
    total_annual_depreciation = 0
    start = None
    end = None

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        tax_settings = TaxSettings.objects.get(Business=buss)

        start = cache.get(f'{buss}_{request.user.id}_profit_and_loss_dash_range_start')
        end = cache.get(f'{buss}_{request.user.id}_profit_and_loss_dash_range_end')

        if start and end:
            (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
             total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

        if request.method == 'POST':
            if 'filter' in request.POST:
                start = request.POST.get('start')
                end = request.POST.get('end')

                (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
                 total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

                assets = Assets.objects.filter(Business=buss)

                # converting html date input into datetime object
                date_format = '%Y-%m-%d'
                start_ = datetime.strptime(start, date_format)
                start_ = start_.replace(tzinfo=timezone.utc)

                end_ = datetime.strptime(end, date_format)
                end_ = start_.replace(tzinfo=timezone.utc)

                cache.set(f'{buss}_{request.user.id}_profit_and_loss_dash_range_start', start_, 300)
                cache.set(f'{buss}_{request.user.id}_profit_and_loss_dash_range_end', end_, 300)

                # annual depreciation is recorded as expense that reduces net-income

                for a in assets:
                    if a.CurrentValue != a.SalvageValue:
                        if a.Date > start_:
                            total_annual_depreciation += a.AnnualDepreciation

                total_expense += total_annual_depreciation

                product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax = \
                    product_revenue(buss, tax_settings, start, end)

                service_income, total_service_income, total_service_vat, total_service_presumptive_tax =\
                    service_revenue(buss, tax_settings, start, end)

                total_debt = debt_total(buss, start, end)

                (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
                 net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand) = \
                    totals_and_profits(buss.id, start, end, tax_settings, total_debt, total_service_vat,
                                       total_product_vat, total_product_presumptive_tax, total_service_presumptive_tax,
                                       total_product_income, total_service_income, cog, total_expense)

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")

    context = {
        'product_income': product_income,
        'total_product_income': total_product_income,
        'service_income': service_income,
        'total_service_income': total_service_income,
        'total_sales': total_sales,
        'total_presumptive_tax': total_presumptive_tax,
        'revenue_after_tax': revenue_after_tax,
        'total_vat': total_vat,
        'cog': cog,
        'gp': gp,
        'op': op,
        'income_in_hand': income_in_hand,
        'paid_for': paid_for,
        'net_profit': net_profit,
        'profit_perc': profit_perc,
        'oe': operational_expense,
        'pe': payroll_expense,
        "discounts": discounts,
        'total_expense': total_expense,
        'oe_total': total_operational_expense,
        'pe_total': total_payroll_expense,
        'total_debt': total_debt,
        'total_credit': total_credit,
        'start': start,
        'end': end
    }
    return render(request, 'profit_and_loss_dash_range.html', context)

