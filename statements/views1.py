from django.shortcuts import render, HttpResponse
from income.models import ProductIncome, ServiceIncome, Service, Package
from inventory.models import InventoryProduct, InventoryProductInfo
from expenses.models import Expense
from django.db.models import Sum, Q
from credits.models import Credit
from datetime import datetime, timedelta, timezone
from calendar import monthrange
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee, Business, CashAccount
from debts.models import Debt
from assets.models import Assets
from User.models import CoreSettings, TaxSettings, TaxAccount, TaxAccountThisYear, TaxInstallments
from .profitAndLoss import (get_tax_year, expenses, product_revenue, service_revenue, debt_total,
                            totals_and_profits)
from expenses.models import Expense, ExpenseAccount


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def profit_and_loss_dash(request):
    total_annual_depreciation = 0

    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business

        tax_settings = TaxSettings.objects.get(Business=buss)
        assets = Assets.objects.filter(Business=buss)

        this_tax_year = get_tax_year(buss)
        start = this_tax_year.TaxYearStart
        end = this_tax_year.TaxYearEnd

        (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
         total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

        # annual depreciation is recorded as expense that reduces net-income
        if assets.exists():
            for a in assets:
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
        'cog': cog,
        'gp': gp,
        'op': op,
        "discounts": discounts,
        "total_discount": total_discount,
        'income_in_hand': income_in_hand,
        'paid_for': paid_for,
        'net_profit': net_profit,
        'profit_perc': profit_perc,
        'oe': operational_expense,
        'pe': payroll_expense,
        'total_expense': total_expense,
        'oe_total': total_operational_expense,
        'pe_total': total_payroll_expense,
        'total_annual_depreciation': total_annual_depreciation,
        'total_debt': total_debt,
        'total_credit': total_credit,
    }
    return render(request, 'profit_and_loss_dash.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def balance_sheet(request):
    try:
        check = Employee.objects.get(User=request.user.id)
        buss = check.Business
        accrued_expenses(buss)
        (total_assets, current_assets, income_in_hand, prepaid_taxes, inventory_value, accounts_receivable,
         receivable, receivable_ty, non_current_assets, property_and_equipment, current_liabilities, taxes_owing,
         total_accrued_expenses, accounts_payable, payable, payable_ty, non_current_liabilities, payable_ny, equity,
         equity_liabilities) = balance_stats(buss)

    except Employee.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'total_assets': total_assets,
        'current_assets': current_assets,
        'cash': income_in_hand,
        'prepaid_taxes': prepaid_taxes,
        'inventory_value': inventory_value,
        'accounts_receivable': accounts_receivable,
        'receivable': receivable,
        'receivable_ty': receivable_ty,
        'non_current_assets': non_current_assets,
        'property_and_equipment': property_and_equipment,
        'current_liabilities': current_liabilities,
        'taxes_owing': taxes_owing,
        'total_accrued_expenses': total_accrued_expenses,
        'accounts_payable': accounts_payable,
        'payable': payable,
        'payable_ty': payable_ty,
        'payable_ny': payable_ny,
        'non_current_liabilities': non_current_liabilities,
        'equity': equity,
        'equity_liabilities': equity_liabilities,
        }
    return render(request, 'balanceSheet.html', context)


def balance_stats(buss):
    current_assets = 0
    property_and_equipment = {}
    total_assets = 0
    current_liabilities = 0
    non_current_liabilities = 0
    total_tax = 0
    tax_installments = 0
    taxes_owing = 0
    prepaid_taxes = 0

    this_tax_year = get_tax_year(buss)
    start = this_tax_year.TaxYearStart
    end = this_tax_year.TaxYearEnd
    tax_settings = TaxSettings.objects.get(Business=buss)
    tax_accounts = TaxAccount.objects.filter(Business=buss)

    cash_account = CashAccount.objects.get(Business=buss)
    cash = cash_account.Value
    if this_tax_year:
        if tax_accounts:
            for a in tax_accounts:
                try:
                    account_this_year = TaxAccountThisYear.objects.get(TaxAccount=a, TaxYear=this_tax_year)
                    total_tax += account_this_year.AccumulatedTotal

                    account_installments = TaxInstallments.objects.filter(TaxAccountThisYear=account_this_year)
                    if account_installments:
                        for i in account_installments:
                            tax_installments += i.Amount
                except TaxAccountThisYear.DoesNotExist:
                    pass

    tax_balance = total_tax - tax_installments
    if tax_balance < 1:
        prepaid_taxes = tax_balance * -1
        current_assets += prepaid_taxes
    else:
        taxes_owing = tax_balance
        current_liabilities += taxes_owing

    assets = Assets.objects.filter(Business=buss)
    non_current_assets = assets.aggregate(Sum('CurrentValue'))
    non_current_assets = non_current_assets['CurrentValue__sum']
    if not non_current_assets:
        non_current_assets = 0

    for a in assets:
        property_and_equipment[a.id] = {'Name': a.Name, 'Amount': a.CurrentValue}

    (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
     total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

    product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax = \
        product_revenue(buss, tax_settings, start, end)

    service_income, total_service_income, total_service_vat, total_service_presumptive_tax = (
        service_revenue(buss, tax_settings, start, end))

    total_debt = debt_total(buss, start, end)

    (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
     net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand) = \
        totals_and_profits(buss.id, start, end, tax_settings, total_debt, total_service_vat, total_product_vat,
                           total_product_presumptive_tax, total_service_presumptive_tax, total_product_income,
                           total_service_income, cog, total_expense)

    # inventory
    inventory_value = InventoryProductInfo.objects.filter(Business=buss).aggregate(Sum('CurrentValue'))
    inventory_value = inventory_value['CurrentValue__sum']
    if not inventory_value:
        inventory_value = 0

    # assets
    accounts_receivable, receivable, receivable_ty = account_receivable(buss, end)

    current_assets += cash + inventory_value + receivable_ty

    total_assets += (current_assets+non_current_assets)

    # liabilities
    accounts_payable, payable, payable_ty, payable_ny = account_payable(buss, end)

    total_accrued_expenses = accrued_expenses(buss)

    current_liabilities += payable_ty + total_accrued_expenses
    non_current_liabilities += payable_ny

    if total_assets != 0:
        if current_liabilities != 0:
            equity = total_assets - current_liabilities - non_current_liabilities
        else:
            equity = total_assets
    else:
        equity = 0

    equity_liabilities = equity + current_liabilities + non_current_liabilities

    return (total_assets, current_assets, cash, prepaid_taxes, inventory_value, accounts_receivable,
            receivable, receivable_ty, non_current_assets, property_and_equipment, current_liabilities, taxes_owing,
            total_accrued_expenses, accounts_payable, payable, payable_ty, non_current_liabilities, payable_ny, equity,
            equity_liabilities)


def account_receivable(buss, end):
    accounts_receivable = {}
    debts = Debt.objects.filter(Business=buss).exclude(Status='Paid')

    """receivable"""
    total_debts = debts.aggregate(Sum('Amount'))
    total_debts = total_debts['Amount__sum']
    if not total_debts:
        total_debts = 0

    received = Debt.objects.filter(Business=buss, Status='Paying').aggregate(Sum('Received'))
    received = received['Received__sum']
    if not received:
        received = 0

    receivable = total_debts - received

    # debts due this year
    debts_due_ty = Debt.objects.filter(Business=buss, Due__lt=end)

    total_debts_ty = debts_due_ty.aggregate(Sum('Amount'))
    total_debts_ty = total_debts_ty['Amount__sum']
    if not total_debts_ty:
        total_debts_ty = 0

    received_ty = debts_due_ty.aggregate(Sum('Received'))
    received_ty = received_ty['Received__sum']
    if not received_ty:
        received_ty = 0

    receivable_ty = total_debts_ty - received_ty

    for i in debts:
        amount = i.Amount
        received = i.Received
        accounts_receivable[i.id] = {'Customer': i.Customer.Name, 'total': amount - received}

    return accounts_receivable, receivable, receivable_ty


def account_payable(buss, end):
    accounts_payable = {}
    credit = Credit.objects.filter(Business=buss).exclude(Status='Paid')

    # payable
    total_credits = credit.aggregate(Sum('Amount'))
    total_credits = total_credits['Amount__sum']
    if not total_credits:
        total_credits = 0

    sent = Credit.objects.filter(Business=buss, Status='Paying').aggregate(Sum('Sent'))
    sent = sent['Sent__sum']
    if not sent:
        sent = 0

    payable = total_credits - sent

    # credits due year
    credits_due_ty = Credit.objects.filter(Business=buss, Due__lt=end)
    total_credits_ty = credits_due_ty.aggregate(Sum('Amount'))
    total_credits_ty = total_credits_ty['Amount__sum']
    if not total_credits_ty:
        total_credits_ty = 0

    sent_ty = credits_due_ty.aggregate(Sum('Sent'))
    sent_ty = sent_ty['Sent__sum']
    if not sent_ty:
        sent_ty = 0

    payable_ty = total_credits_ty - sent_ty
    payable_ny = payable - payable_ty

    for i in credit:
        amount = i.Amount
        sent = i.Sent
        accounts_payable[i.id] = {'Supplier': i.Supplier.Name, 'total': amount - sent}

    return accounts_payable, payable, payable_ty, payable_ny


def accrued_expenses(buss):
    accrued_expenses_total = 0
    actual_total = 0
    today = datetime.now(timezone.utc)

    accounts = ExpenseAccount.objects.filter(Business=buss)
    # expense = Expense.objects.filter(Business=buss, ExpenseAccount__isnull=False)

    for a in accounts:
        if a.Interval == 'Weekly':
            expense = Expense.objects.filter(Business=buss, ExpenseAccount=a)
            if expense:
                accrued_expenses_total += accrued_calculater(expense, today, 7)

        if a.Interval == 'Monthly':
            expense = Expense.objects.filter(Business=buss, ExpenseAccount=a)
            if expense:
                # on average 30.44 days make a month
                accrued_expenses_total += accrued_calculater(expense, today, 30)

        if a.Interval == 'Annually':
            expense = Expense.objects.filter(Business=buss, ExpenseAccount=a)
            if expense:
                # on average 365.5 days make a year
                accrued_expenses_total += accrued_calculater(expense, today, 365)

    return accrued_expenses_total


def accrued_calculater(expense, today, interval):
    # to get the accumulated total we are multiplying the average price
    # by the period in which payments are absent
    date_difference = (today.date() - expense.last().Date.date()).days
    actual_total = expense.aggregate(Sum('Price'))
    actual_total = actual_total['Price__sum']

    average_price = actual_total/expense.count()
    accumulated_total = average_price * (date_difference // interval)
    if actual_total < 1:
        accumulated_total = 0

    return round(accumulated_total)
