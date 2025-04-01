from django.shortcuts import render, HttpResponse
from income.models import ProductIncome, ServiceIncome, Service, Package
from inventory.models import InventoryProduct, InventoryProductInfo
from expenses.models import Expense, ExpenseAccount
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from User.models import Employee, TaxSettings
from statements.views1 import get_tax_year


def product_stats(buss, start, end):
    credit = 0
    product_revenue_cash = 0
    product_revenue_credit = 0
    total_cog = 0
    product_income = {}

    income = ProductIncome.objects.filter(Business=buss, Date__range=(start, end))
    total_product_revenue = income.aggregate(Sum('Amount'))
    total_product_revenue = total_product_revenue['Amount__sum']
    if not total_product_revenue:
        total_product_revenue = 0

    if income.exists():
        for i in income:
            if i.PMode == 'Credit':
                product_revenue_credit += i.Amount

    product_revenue_cash = total_product_revenue - product_revenue_credit

    products = InventoryProduct.objects.filter(Business=buss)
    for p in products:
        prod_info = InventoryProductInfo.objects.get(Product=p.id)
        inc = ProductIncome.objects.filter(Business=buss, Product=p, Date__range=(start, end))

        total = inc.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        for i in inc:
            if i.PMode == 'Credit':
                credit += i.Amount

        quantity = inc.aggregate(Sum('Quantity'))
        quantity = quantity['Quantity__sum']
        if not quantity:
            quantity = 0
        cog = prod_info.BPrice * quantity
        total_cog += prod_info.BPrice * quantity

        product_income[p.id] = {}
        product_income[p.id]['Name'] = p.Name
        product_income[p.id]['Cash'] = total-credit
        product_income[p.id]['Credit'] = credit
        product_income[p.id]['total'] = total
        product_income[p.id]['COG'] = cog

        credit = 0

    return total_product_revenue, product_revenue_cash, product_revenue_credit, total_cog, product_income


def service_stats(buss, start, end):
    credit = 0
    service_revenue_cash = 0
    service_revenue_credit = 0
    service_totals = {}
    service_income = {}

    income_in_general = ServiceIncome.objects.filter(Date__range=(start, end))

    total_service_revenue = income_in_general.aggregate(Sum('Amount'))
    total_service_revenue = total_service_revenue['Amount__sum']
    if not total_service_revenue:
        total_service_revenue = 0

    if income_in_general.exists():
        for i in income_in_general:
            if i.PMode == 'Credit':
                credit += i.Amount
        service_revenue_cash = total_service_revenue - credit
        service_revenue_credit = credit
        credit = 0

    package_total = (ServiceIncome.objects.filter(Date__range=(start, end), Package__isnull=False).
                     aggregate(Sum('Amount')))
    package_total = package_total['Amount__sum']
    if not package_total:
        package_total = 0

    service_total = (ServiceIncome.objects.filter(Date__range=(start, end), Service__isnull=False).
                     aggregate(Sum('Amount')))
    service_total = service_total['Amount__sum']
    if not service_total:
        service_total = 0

    services = Service.objects.filter(Business=buss)
    packages = Package.objects.filter(Business=buss)

    for s in services:
        service_inc = ServiceIncome.objects.filter(Service=s, Date__range=(start, end))
        total = service_inc.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        for i in service_inc:
            if service_inc.exists():
                if i.PMode == 'Credit':
                    credit += i.Amount
        service_income[s.id] = {}
        service_income[s.id]['Name'] = s.Name
        service_income[s.id]['total'] = total
        service_income[s.id]['Cash'] = total-credit
        service_income[s.id]['Credit'] = credit

        credit = 0

    for p in packages:
        package_inc = ServiceIncome.objects.filter(Package=p, Date__range=(start, end))
        total = package_inc.aggregate(Sum('Amount'))
        total = total['Amount__sum']
        if not total:
            total = 0

        for i in package_inc:
            if package_inc.exists():
                if i.PMode == 'Credit':
                    credit += i.Amount
        service_income[p.id] = {}
        service_income[p.id]['Name'] = p.Name
        service_income[p.id]['total'] = total
        service_income[p.id]['Cash'] = total-credit
        service_income[p.id]['Credit'] = credit

        credit = 0

    return total_service_revenue, service_revenue_cash, service_revenue_credit, service_income


def expense_stats(buss, start, end):
    credit = 0
    total_expense_cash = 0
    total_expense_credit = 0
    expense_totals = {}
    expense_accounts = {}

    # all expenses
    expenses_in_general = (Expense.objects.filter(Business=buss, Date__range=(start, end)).
                           exclude(Q(Type='Stock') | Q(Type='Asset')))
    total_expenses = expenses_in_general.aggregate(Sum('Price'))
    total_expenses = total_expenses['Price__sum']
    if not total_expenses:
        total_expenses = 0

    if expenses_in_general.exists():
        for i in expenses_in_general:
            if i.PMode == 'Credit':
                credit += i.Price

        total_expense_cash = total_expenses - credit
        total_expense_credit = credit
        credit = 0

    # operating expenses
    e_type = ['Operational', 'Payroll', 'Stock']
    for et in e_type:
        expense = Expense.objects.filter(Business=buss, Date__range=(start, end), Type=et)
        total = expense.aggregate(Sum('Price'))
        total = total['Price__sum']
        if not total:
            total = 0
        if expense.exists():
            for e in expense:
                credit += e.Price
        expense_totals[et] = {}
        expense_totals[et]['total'] = total
        expense_totals[et]['cash'] = total-credit
        expense_totals[et]['credit'] = credit
        credit = 0

    accounts = ExpenseAccount.objects.filter(Business=buss)
    for a in accounts:
        account = Expense.objects.filter(Business=buss, Date__range=(start, end), ExpenseAccount=a)
        total = account.aggregate(Sum('Price'))
        total = total['Price__sum']
        if not total:
            total = 0

        if account.exists():
            for i in account:
                if i.PMode == 'Credit':
                    credit += i.Price

        expense_accounts[a.id] = {}
        expense_accounts[a.id]['Name'] = a.Name
        expense_accounts[a.id]['cash'] = total-credit
        expense_accounts[a.id]['credit'] = credit
        credit = 0

    return total_expenses, total_expense_cash, total_expense_credit, expense_totals, expense_accounts


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def double_entry(request):
    total_revenue = 0
    revenue_cash = 0
    accounts_receivable = 0
    total = 0
    try:
        check = Employee.objects.get(User=request.User.id)
        buss = check.Business

        this_tax_year = get_tax_year(buss)
        start = this_tax_year.TaxYearStart
        end = this_tax_year.TaxYearEnd

        total_product_revenue, product_revenue_cash, product_revenue_credit, total_cog, product_income = (
            product_stats(buss, start, end))
        total_service_revenue, service_revenue_cash, service_revenue_credit, service_income = (
            service_stats(buss, start, end))
        total_expenses, total_expense_cash, total_expense_credit, expense_totals, expense_accounts = expense_stats(buss, start, end)

        if total_service_revenue and total_product_revenue:
            total_revenue = total_product_revenue + total_service_revenue
        elif total_product_revenue and not total_service_revenue:
            total_revenue = total_product_revenue
        elif total_service_revenue and not total_product_revenue:
            total_revenue = total_service_revenue

        if product_revenue_cash and service_revenue_cash:
            revenue_cash = product_revenue_cash + service_revenue_cash
        elif product_revenue_cash and not service_revenue_cash:
            revenue_cash = product_revenue_cash
        elif service_revenue_cash and not product_revenue_cash:
            revenue_cash = service_revenue_cash

        if product_revenue_credit and service_revenue_credit:
            accounts_receivable = product_revenue_credit + service_revenue_credit
        elif product_revenue_credit and not service_revenue_credit:
            accounts_receivable = product_revenue_credit
        elif service_revenue_credit and not product_revenue_credit:
            accounts_receivable = service_revenue_credit

        total += total_revenue + total_cog + total_expenses
    except Employee.DoesNotExist:
        return HttpResponse("Failed to process your profile please try refreshing your browser or contact developer if"
                            "the problem persists")
    context = {
        'total': total,
        'total_revenue': total_revenue,
        'revenue_cash': revenue_cash,
        'accounts_receivable': accounts_receivable,
        'product_income': product_income,
        'total_cog': total_cog,
        'service_income': service_income,
        'total_expenses': total_expenses,
        'total_expense_cash': total_expense_cash,
        'total_expense_credit': total_expense_credit,
        'expense_totals': expense_totals,
        'expense_accounts': expense_accounts
    }
    return render(request, 'doubleEntry.html', context)
