from django.shortcuts import render, HttpResponse, redirect
from income.models import ProductIncome, ServiceIncome, Service, Package
from User.models import TaxSettings
from expenses.models import Expense
from inventory.models import InventoryProduct, InventoryProductInfo
from django.db.models import Sum, Q
from credits.models import Credit
from debts.models import Debt
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from assets.models import Assets, Shareholders
from User.models import CoreSettings, CashAccount, TaxYear, TaxAccount, TaxAccountThisYear


def get_tax_year(buss):
    today = datetime.now(timezone.utc)
    try:
        this_year = TaxYear.objects.get(Business=buss, TaxYearStart__lte=today, TaxYearEnd__gte=today)
    except TaxYear.DoesNotExist:
        this_year = None
    return this_year


def expenses(buss, start, end):
    total_credit = 0
    paid_for = 0

    # all expenses
    total_expense = (Expense.objects.filter(Business=buss, Date__range=(start, end)).
                     exclude(Q(Type='Stock') | Q(Type='Asset')).aggregate(Sum('Price')))
    total_expense = total_expense['Price__sum']
    if not total_expense:
        total_expense = 0
    # operating expenses
    operational_expense = Expense.objects.filter(Business=buss, Date__range=(start, end), Type='Operational')

    total_operational_expense = (Expense.objects.filter(Business=buss, Date__range=(start, end), Type='Operational').
                                 aggregate(Sum('Price')))
    total_operational_expense = total_operational_expense['Price__sum']

    if not total_operational_expense:
        total_operational_expense = 0

    # payroll expenses
    payroll_expense = Expense.objects.filter(Business=buss, Date__range=(start, end), Type='Payroll')

    total_payroll_expense = (Expense.objects.filter(Business=buss, Date__range=(start, end), Type='Payroll').
                             aggregate(Sum('Price')))
    total_payroll_expense = total_payroll_expense['Price__sum']
    if not total_payroll_expense:
        total_payroll_expense = 0

    # expenses on credit
    credit = (Credit.objects.filter(Business=buss, Date__range=(start, end)).exclude(Status='Paid').
              aggregate(Sum('Amount')))
    credit = credit['Amount__sum']
    if not credit:
        credit = 0

    p_credit_sent = Credit.objects.filter(Business=buss, Status='Paying', Date__range=(start, end)).aggregate(Sum('Sent'))
    p_credit_sent = p_credit_sent['Sent__sum']
    if not p_credit_sent:
        p_credit_sent = 0

    if credit:
        if p_credit_sent:
            total_credit = credit - p_credit_sent
        else:
            total_credit = credit

    if total_expense:
        print('TE==============================================', total_expense)
        if total_expense < total_credit:
            paid_for = 0
        else:
            paid_for = total_expense - total_credit
            print('paid_for==============================================', paid_for)

    return (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
            total_payroll_expense)


def product_revenue(buss, tax_settings,  start, end):
    product_income = {}
    cog = 0
    total_product_vat = 0

    # product income
    prod_income = ProductIncome.objects.filter(Business=buss, Date__range=(start, end))
    total_product_income = prod_income.aggregate(Sum('Amount'))
    total_product_income = total_product_income['Amount__sum']
    if not total_product_income:
        total_product_income = 0
    total_product_income = round(total_product_income)

    if tax_settings.ShowEstimates and tax_settings.IncludeVAT:
        try:
            total_product_vat = round((total_product_income * tax_settings.VATRate) / 100)
        except ZeroDivisionError:
            pass

    """income record per inventory item"""
    prod = InventoryProduct.objects.filter(Business=buss)

    for p in prod:
        prod_info = InventoryProductInfo.objects.get(Product=p.id)
        inc = ProductIncome.objects.filter(Business=buss, Code=prod_info.Code, Date__range=(start, end))

        total = inc.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        quantity = inc.aggregate(Sum('Quantity'))
        quantity = quantity['Quantity__sum']
        if not quantity:
            quantity = 0
        cog += prod_info.BPrice * quantity

        product_income[p.id] = {}
        product_income[p.id]['Name'] = p.Name
        product_income[p.id]['cog'] = prod_info.BPrice * quantity
        product_income[p.id]['revenue'] = total
    return product_income, total_product_income, cog, total_product_vat


def service_revenue(buss, tax_settings, start, end):
    total_service_vat = 0
    service_income = {}

    # all income
    # service income
    services = Service.objects.filter(Business=buss)
    packages = Package.objects.filter(Business=buss)
    for s in services:
        total = ServiceIncome.objects.filter(Service=s, Date__range=(start, end)).aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        service_income[s.id] = {}
        service_income[s.id]['Name'] = s.Name
        service_income[s.id]['Amount'] = total

    for p in packages:
        total = ServiceIncome.objects.filter(Package=p, Date__range=(start, end)).aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        service_income[p.id] = {}
        service_income[p.id]['Name'] = p.Name
        service_income[p.id]['Amount'] = total

    total_service_income = ServiceIncome.objects.filter(Business=buss, Date__range=(start, end)).aggregate(
        Sum('Amount'))
    total_service_income = total_service_income['Amount__sum']
    if not total_service_income:
        total_service_income = 0
    total_service_income = round(total_service_income)

    if tax_settings.ShowEstimates and tax_settings.IncludeVAT:
        try:
            total_service_vat = round((total_service_income * tax_settings.VATRate) / 100)
        except ZeroDivisionError:
            pass

    service_income['VAT'] = {}
    service_income['VAT']['Name'] = 'Service VAT'
    service_income['VAT']['Amount'] = total_service_vat
    return service_income, total_service_income, total_service_vat


def debt_total(buss, start, end):
    total_debt = 0
    # income in debts
    debt = Debt.objects.filter(Business=buss, Date__range=(start, end)).exclude(Status='Paid').aggregate(Sum('Amount'))
    debt = debt['Amount__sum']
    if not debt:
        debt = 0

    p_debt_received = Debt.objects.filter(Business=buss, Status='Paying', Date__range=(start, end)).aggregate(
        Sum('Received'))
    p_debt_received = p_debt_received['Received__sum']
    if not p_debt_received:
        p_debt_received = 0

    if debt and p_debt_received:
        total_debt = debt - p_debt_received
    elif debt and not p_debt_received:
        total_debt = debt

    return total_debt


def totals_and_profits(tax_settings, total_debt, total_service_vat, total_product_vat, total_product_income,
                       total_service_income, cog, total_expense):

    income_in_hand = 0
    revenue_after_vat = 0

    total_vat = total_service_vat + total_product_vat

    total_sales = total_product_income + total_service_income

    # gross profit
    gp = total_sales - cog

    """operating profit(profit after deducting all costs except credits"""
    if not total_expense:
        total_expense = 0

    op = total_sales - total_expense

    if tax_settings.IncludeVAT:
        net_profit = (gp - total_expense - total_vat)
    else:
        net_profit = gp - total_expense

    try:
        profit_perc = round(net_profit / total_sales * 100)
    except ZeroDivisionError:
        profit_perc = 0

    # cash in hand
    if total_debt:
        income_in_hand = total_sales - total_debt
    else:
        income_in_hand = total_sales

    # Revenue after vat
    if tax_settings.ShowEstimates and tax_settings.IncludeVAT:
        revenue_after_vat = total_sales - total_vat

    return total_sales, total_vat, gp, op, net_profit, profit_perc, revenue_after_vat, income_in_hand


def pay_out(buss, net_profit):
    pay_out_ratio = 0
    retained_earnings = 0
    total = 0
    pay_out_percentage = 0
    dividends = {}
    cash_account = CashAccount.objects.get(Business=buss)
    if cash_account.TotalShares:
        total_shares = cash_account.TotalShares
    else:
        total_shares = 0
    shareholders = Shareholders.objects.filter(Business=buss)

    if cash_account.PayoutRatio:
        pay_out_ratio = cash_account.PayoutRatio/100

    try:
        dividends_per_share = round(((net_profit * pay_out_ratio) / total_shares), 1)

    except ZeroDivisionError:
        dividends_per_share = 0

    total_dividends = round(dividends_per_share * total_shares)
    retained_earnings = net_profit - total_dividends

    for sh in shareholders:
        try:
            pay_out_percentage = (sh.Shares / total_shares) * 100
        except ZeroDivisionError:
            pay_out_percentage = 0
        dividends[sh] = {}
        dividends[sh]['shares'] = sh.Shares
        dividends[sh]['pay_out_percentage'] = pay_out_percentage
        dividends[sh]['total_dividends'] = total_dividends * (pay_out_percentage/100)

    return total_dividends, dividends, retained_earnings


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def profit_and_loss(request):
    total_annual_depreciation = 0

    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business

        tax_settings = TaxSettings.objects.get(Business=buss)

        this_tax_year = get_tax_year(buss)
        start = this_tax_year.TaxYearStart
        end = this_tax_year.TaxYearEnd

        (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
         total_payroll_expense) = expenses(buss, start, end)

        assets = Assets.objects.filter(Business=buss)

        # annual depreciation is recorded as expense that reduces net-income
        if assets.exists():
            for a in assets:
                total_annual_depreciation += a.AnnualDepreciation

        total_expense += total_annual_depreciation

        paid_for += total_annual_depreciation

        product_income, total_product_income, cog, total_product_vat = product_revenue(buss, tax_settings, start, end)
        service_income, total_service_income, total_service_vat = service_revenue(buss, tax_settings, start, end)
        total_debt = debt_total(buss, start, end)
        total_sales, total_vat, gp, op, net_profit, profit_perc, revenue_after_vat, income_in_hand = (
            totals_and_profits(tax_settings, total_debt, total_service_vat, total_product_vat, total_product_income,
                               total_service_income, cog, total_expense))
        total_dividends, dividends, retained_earnings = pay_out(buss, net_profit)

    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")
    context = {
        'product_income': product_income,
        'total_product_income': total_product_income,
        'service_income': service_income,
        'total_service_income': total_service_income,
        'total_sales': total_sales,
        'total_vat': total_vat,
        'revenue_after_vat': revenue_after_vat,
        'income_in_hand': income_in_hand,
        'paid_for': paid_for,
        'oe': operational_expense,
        'pe': payroll_expense,
        'total_expense': total_expense,
        'oe_total': total_operational_expense,
        'pe_total': total_payroll_expense,
        'total_annual_depreciation': total_annual_depreciation,
        'total_debt': total_debt,
        'total_credit': total_credit,
        'cog': cog,
        'gp': gp,
        'op': op,
        'net_profit': net_profit,
        'profit_perc': profit_perc,
    }
    return render(request, 'profit_and_Loss.html', context)
