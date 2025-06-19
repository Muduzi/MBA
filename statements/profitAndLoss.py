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
from assets.models import Assets
from User.models import CashAccount, TaxYear
from management.views import presumptive_tax_calculator, income_tax_calculator
from dateutil.relativedelta import relativedelta
from management.views import total_salary_and_paye


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
    total_discount = 0
    discounts = {}

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
        if total_expense < total_credit:
            paid_for = 0
        else:
            paid_for = total_expense - total_credit

    # income record per inventory item
    prod = InventoryProduct.objects.filter(Business=buss)

    for p in prod:
        prod_info = InventoryProductInfo.objects.get(Product=p.id)
        inc = ProductIncome.objects.filter(Business=buss, Code=prod_info.Code, Date__range=(start, end), Discount=True)

        total_product_revenue = inc.aggregate(Sum('Amount'))
        total_product_revenue = total_product_revenue['Amount__sum']
        if not total_product_revenue:
            total_product_revenue = 0

        total_product_quantity = inc.aggregate(Sum('Quantity'))
        total_product_quantity = total_product_quantity['Quantity__sum']
        if not total_product_quantity:
            total_product_quantity = 0

        discount = (prod_info.SPrice * total_product_quantity) - total_product_revenue
        if discount > 1:
            discounts[p.id] = {'revenue_type': 'products', 'Name': p.Name, 'Amount': discount}
            total_discount += discount

    # income records per service or package
    services = Service.objects.filter(Business=buss)
    packages = Package.objects.filter(Business=buss)
    for s in services:
        service_ = ServiceIncome.objects.filter(Service=s, Date__range=(start, end), Discount=True)

        service_total = service_.aggregate(Sum('Amount'))
        service_total = service_total['Amount__sum']
        if not service_total:
            service_total = 0

        service_quantity = service_.aggregate(Sum('Quantity'))
        service_quantity = service_quantity['Quantity__sum']
        if not service_quantity:
            service_quantity = 0

        discount = (s.Price * service_quantity) - service_total
        if discount > 1:
            total_discount += discount
            discounts[s.id] = {'revenue_type': 'services', 'Name': s.Name, 'Amount': discount}

    for p in packages:
        package_ = ServiceIncome.objects.filter(Package=p, Date__range=(start, end), Discount=True)

        package_total = package_.aggregate(Sum('Amount'))
        package_total = package_total['Amount__sum']
        if not package_total:
            package_total = 0

        package_quantity = package_.aggregate(Sum('Quantity'))
        package_quantity = package_quantity['Quantity__sum']
        if not package_quantity:
            package_quantity = 0

        discount = (p.Price * package_quantity) - package_total
        if discount > 1:
            total_discount += discount
            discounts[p.id] = {'revenue_type': 'services', 'Name': p.Name, 'Amount': discount}

    if total_discount > 1:
        total_expense += total_discount

    return (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
            total_payroll_expense, total_discount, discounts)


def product_revenue(buss, tax_settings,  start, end):
    product_income = {}
    cog = 0
    total_product_vat = 0
    total_product_presumptive_tax = 0

    # product income
    prod_income = ProductIncome.objects.filter(Business=buss, Date__range=(start, end))
    total_product_income = prod_income.aggregate(Sum('Amount'))
    total_product_income = total_product_income['Amount__sum']
    if not total_product_income:
        total_product_income = 0
    total_product_income = round(total_product_income)

    if tax_settings.ShowEstimates:
        if tax_settings.IncludeVAT:
            try:
                total_product_vat = round(total_product_income * (tax_settings.VATRate / 100))
            except ZeroDivisionError:
                pass
        elif tax_settings.IncludePresumptiveTax:
            total_product_presumptive_tax = presumptive_tax_calculator(total_product_income)

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

        product_income[p.id] = {'Name': p.Name, 'cog': prod_info.BPrice * quantity, 'revenue': total}
    return product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax


def service_revenue(buss, tax_settings, start, end):
    total_service_vat = 0
    total_service_presumptive_tax = 0
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

        service_income[s.id] = {'Name': s.Name, 'Amount': total}

    for p in packages:
        total = ServiceIncome.objects.filter(Package=p, Date__range=(start, end)).aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        service_income[p.id] = {'Name': p.Name, 'Amount': total}

    total_service_income = ServiceIncome.objects.filter(Business=buss, Date__range=(start, end)).aggregate(
        Sum('Amount'))
    total_service_income = total_service_income['Amount__sum']
    if not total_service_income:
        total_service_income = 0
    total_service_income = round(total_service_income)

    if tax_settings.ShowEstimates:
        if tax_settings.IncludeVAT:
            try:
                total_service_vat = round(total_service_income * (tax_settings.VATRate / 100))
                total_service_presumptive_tax = 0
            except ZeroDivisionError:
                pass
        elif tax_settings.IncludePresumptiveTax:
            total_service_presumptive_tax = presumptive_tax_calculator(total_service_income)
            total_service_vat = 0

    return service_income, total_service_income, total_service_vat, total_service_presumptive_tax


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


def totals_and_profits(buss_id, start, end, tax_settings, total_debt, total_service_vat, total_product_vat,
                       total_product_presumptive_tax, total_service_presumptive_tax, total_product_income,
                       total_service_income, cog, total_expense):

    income_in_hand = 0
    revenue_after_tax = 0
    total_vat = 0
    total_presumptive_tax = 0
    income_tax = 0
    profit_after_income_tax = 0

    total_sales = total_product_income + total_service_income

    # gross profit
    gp = total_sales - cog

    """operating profit(profit after deducting all costs except credits"""
    if not total_expense:
        total_expense = 0

    # operational profit
    op = gp - total_expense

    # Revenue after vat
    if tax_settings.ShowEstimates:
        if tax_settings.IncludeVAT:
            total_vat = total_service_vat + total_product_vat
            revenue_after_tax = op - total_vat

        elif tax_settings.IncludePresumptiveTax:
            total_presumptive_tax = total_product_presumptive_tax + total_service_presumptive_tax
            revenue_after_tax = op - total_presumptive_tax
    else:
        revenue_after_tax = op

    # net profit and profit percentage(margin)
    net_profit = (revenue_after_tax - total_expense)

    try:
        profit_perc = round(net_profit / total_sales * 100)
    except ZeroDivisionError:
        profit_perc = 0

    # profit after tax(income tax)
    # income tax is paid on profits if annual turnover exceeds 12,500,000
    if tax_settings.IncludeIncomeTax:
        income_tax = income_tax_calculator(net_profit)
        profit_after_income_tax = net_profit - income_tax

    # cash in hand
    if total_debt:
        income_in_hand = total_sales - total_debt
    else:
        income_in_hand = total_sales

    return (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
            net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand)


# this app works on the assumption that the business is under sore proprietorship
def pay_out(buss, net_profit):
    pay_out_ratio = 0
    cash_account = CashAccount.objects.get(Business=buss)

    if cash_account.PayoutRatio:
        pay_out_ratio = cash_account.PayoutRatio/100

    try:
        total_dividends = round((net_profit * pay_out_ratio), 2)
    except ZeroDivisionError:
        total_dividends = 0

    retained_earnings = net_profit - total_dividends

    return total_dividends, retained_earnings


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def profit_and_loss(request):
    total_annual_depreciation = 0
    today = datetime.now().date()
    try:
        user_object = request.user
        check = Employee.objects.get(User=user_object.id)
        buss = check.Business

        tax_settings = TaxSettings.objects.get(Business=buss)

        this_tax_year = get_tax_year(buss)
        start = this_tax_year.TaxYearStart
        end = this_tax_year.TaxYearEnd

        (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
         total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

        assets = Assets.objects.filter(Business=buss)

        # annual depreciation is recorded as expense that reduces net-income
        if assets.exists():
            for a in assets:
                if (a.Date.date - today) < (a.Date + relativedelta(years=a.UsefulLife)):
                    total_annual_depreciation += a.AnnualDepreciation

        total_expense += total_annual_depreciation

        paid_for += total_annual_depreciation

        product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax =\
            product_revenue(buss, tax_settings, start, end)

        service_income, total_service_income, total_service_vat, total_service_presumptive_tax =\
            service_revenue(buss, tax_settings, start, end)

        total_debt = debt_total(buss, start, end)

        (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
         net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand) = \
            totals_and_profits(buss.id, start, end, tax_settings, total_debt, total_service_vat, total_product_vat,
                               total_product_presumptive_tax, total_service_presumptive_tax, total_product_income,
                               total_service_income, cog, total_expense)

        total_dividends, retained_earnings = pay_out(buss, net_profit)

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
        'total_presumptive_tax': total_presumptive_tax,
        'revenue_after_tax': revenue_after_tax,
        'income_in_hand': income_in_hand,
        'paid_for': paid_for,
        'oe': operational_expense,
        'pe': payroll_expense,
        'total_expense': total_expense,
        'oe_total': total_operational_expense,
        'pe_total': total_payroll_expense,
        'total_annual_depreciation': total_annual_depreciation,
        'total_discount': total_discount,
        'discounts': discounts,
        'total_debt': total_debt,
        'total_credit': total_credit,
        'cog': cog,
        'gp': gp,
        'op': op,
        'net_profit': net_profit,
        'income_tax': income_tax,
        'profit_after_income_tax': profit_after_income_tax,
        'profit_perc': profit_perc
    }
    return render(request, 'profit_and_Loss.html', context)
