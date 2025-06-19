from django.shortcuts import (render, redirect, HttpResponse)
from django.contrib.auth.models import User, Group
from django.contrib import messages
from User.models import Profile, Department, Business, Employee, EmployeeAllowance, Allowance
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from User.decorator import allowed_users
from django.db.models import Sum, Q
from datetime import datetime, timedelta, timezone
from calendar import monthrange
from .models import (CoreSettings, CashAccount, TaxSettings, TaxYear, TaxAccount, TaxAccountThisYear, TaxInstallments,
                     Salary, Allowance, EmployeeIncentives, BusinessDashContent)
from statements.profitAndLoss import (get_tax_year, expenses, product_revenue, service_revenue, debt_total,
                                      totals_and_profits, pay_out)
from income.product_income_dash import product_monthly_records_this_year, product_daily_records_this_month
from income.service_income_dash import service_monthly_records_this_year, services_daily_records_this_month
from expenses.models import ExpenseAccount
from expenses.expenses_dash import monthly_expenses_this_year, daily_expenses_this_month
from income.invoice import get_invoices
from django.core.cache import cache
from celery import shared_task
from management.models import PayAsYouEarn, PayAsYouEarnThreshold
from management.views import (pay_as_you_earn_calculator, presumptive_tax_calculator, income_tax_calculator,
                              total_salary_and_paye)


def find_user(search_item):
    search_result = User.objects.filter(username__contains=search_item)

    return search_result


@login_required(login_url="/login/")
def business(request):
    start_date = '0000-00-00'
    search_result = {}
    value = 0
    total_debt = 0
    income_in_hand = 0
    total_credit = 0
    paid_for = 0
    net_profit = 0
    profit_perc = 0
    delta_funds_percentage = 0
    total_dividends = 0
    dividends = 0
    retained_earnings = 0
    delta_funds_percentage_remainder = 0
    amount = 0
    income_record = {}
    expense_record = {}
    total_expenses = 0
    total_income = 0

    months = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
              7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
    try:
        buss = Business.objects.get(Owner=request.user.id)
        buss_id = buss.id

        try:
            core_settings = CoreSettings.objects.get(Business__id=buss_id)
        except CoreSettings.DoesNotExist:
            core_settings = CoreSettings(Business=buss, Value=0)
            core_settings.save()

        try:
            tax_settings = TaxSettings.objects.get(Business__id=buss_id)
        except TaxSettings.DoesNotExist:
            tax_settings = TaxSettings(Business=buss).save()

        try:
            cash_account = CashAccount.objects.get(Business__id=buss_id)
        except CashAccount.DoesNotExist:
            cash_account = CashAccount(Business=buss, Value=0, PayoutRatio=20)
            cash_account.save()
        pay_out_ratio_remainder = 100 - cash_account.PayoutRatio

        try:
            content = BusinessDashContent.objects.get(Business__id=buss_id, Cashier=request.user)
        except BusinessDashContent.DoesNotExist:
            content = BusinessDashContent(Business=buss, Cashier=request.user, Choice='This Year')
            content.save()

        try:
            TaxYear.objects.get(Business__id=buss_id, TaxYearStart=core_settings.StartBusinessYear)
        except TaxYear.DoesNotExist:
            if core_settings.StartBusinessYear:
                tax_this_year = TaxYear(Business=buss, TaxYearStart=core_settings.StartBusinessYear,
                                        TaxYearEnd=core_settings.StartBusinessYear + timedelta(days=365))
                tax_this_year.save()

        if core_settings.StartBusinessYear:
            if len(str(core_settings.StartBusinessYear.day)) == 1:
                day = f'0{core_settings.StartBusinessYear.day}'
            else:
                day = core_settings.StartBusinessYear.day
            if len(str(core_settings.StartBusinessYear.month)) == 1:
                month = f'0{core_settings.StartBusinessYear.month}'
            else:
                month = core_settings.StartBusinessYear.month

            start_date = f"{core_settings.StartBusinessYear.year}-{month}-{day}"

        tax_this_year = get_tax_year(buss_id)
        if not tax_this_year:
            messages.info(request, 'Tax(business) year start and end are not set, fill in the form below to set'
                                   ' it up')
        elif tax_this_year:
            start = tax_this_year.TaxYearStart
            end = tax_this_year.TaxYearEnd

            (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
             total_payroll_expense, total_discount, discounts) = expenses(buss_id, start, end)

            product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax = (
                product_revenue(buss_id, tax_settings, start, end))

            service_income, total_service_income, total_service_vat, total_service_presumptive_tax = (
                service_revenue(buss_id, tax_settings, start, end))

            total_debt = debt_total(buss_id, start, end)

            (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
                net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand) =\
                totals_and_profits(buss_id, start, end, tax_settings, total_debt, total_service_vat, total_product_vat,
                                   total_product_presumptive_tax, total_service_presumptive_tax, total_product_income,
                                   total_service_income, cog, total_expense)

            total_dividends, retained_earnings = pay_out(buss_id, net_profit)

            # income_expense graph(business overview)
            #  this year

            # service_monthly_records_this_year
            service_monthly_records_this_year.delay(buss_id)
            total_service_income_y = cache.get(str(buss_id) + 's_m_r_t_y-total')
            cash_service_income_y = cache.get(str(buss_id) + 's_m_r_t_y-cash')
            credit_service_income_y = cache.get(str(buss_id) + 's_m_r_t_y-credit')
            service_income_this_year = cache.get(str(buss_id) + 's_m_r_t_y-income_this_year')

            if (not total_service_income_y and not cash_service_income_y and not credit_service_income_y
                    and not service_income_this_year):
                total_service_income_y, cash_service_income_y, credit_service_income_y, service_income_this_year = (
                    service_monthly_records_this_year(buss_id))

            # product_monthly_records_this_year
            product_monthly_records_this_year.delay(buss_id)
            total_product_income_y = cache.get(str(buss_id) + 'p_m_r_t_y-total')
            cash_product_income_y = cache.get(str(buss_id) + 'p_m_r_t_y-cash')
            credit_product_income_y = cache.get(str(buss_id) + 'p_m_r_t_y-credit')
            products_income_this_year = cache.get(str(buss_id) + 'p_m_r_t_y-product_income_this_year')

            if (not total_product_income_y and not cash_product_income_y and not credit_product_income_y
                    and not products_income_this_year):
                total_product_income_y, cash_product_income_y, credit_product_income_y, products_income_this_year =\
                    product_monthly_records_this_year(buss_id)

            # monthly_expenses_this_year
            monthly_expenses_this_year.delay(buss_id)
            total_expenses_y = cache.get(str(buss_id) + 'm_e_t_y-total')
            cash_expenses_y = cache.get(str(buss_id) + 'm_e_t_y-cash')
            credit_expenses_y = cache.get(str(buss_id) + 'm_e_t_y-credit')
            monthly_expense_record_y = cache.get(str(buss_id) + 'm_e_t_y-monthly_expense_records')
            suppliers_y = cache.get(str(buss_id) + 'm_e_t_y-suppliers_y')
            expenses_this_year = cache.get(str(buss_id) + 'm_e_t_y-expenses_this_year')

            if (not total_expenses_y and not cash_expenses_y and not credit_expenses_y and
                    not monthly_expense_record_y and not expenses_this_year):
                (total_expenses_y, cash_expenses_y, credit_expenses_y, monthly_expense_record_y, suppliers_y,
                 expenses_this_year) = monthly_expenses_this_year(buss_id)

            # this month

            # product_daily_records_this_month
            product_daily_records_this_month.delay(buss_id)
            total_product_income_m = cache.get(str(buss_id) + 'p_d_r_t_m-total')
            cash_product_income_m = cache.get(str(buss_id) + 'p_d_r_t_m-cash')
            credit_product_income_m = cache.get(str(buss_id) + 'p_d_r_t_m-credit')
            products_income_this_month = cache.get(str(buss_id) + 'p_d_r_t_m-income_this_month')

            if (not total_product_income_m and not cash_product_income_m and not credit_product_income_m and
                    not products_income_this_month):
                total_product_income_m, cash_product_income_m, credit_product_income_m, products_income_this_month =\
                    product_daily_records_this_month(buss_id)

            # services_daily_records_this_month
            services_daily_records_this_month.delay(buss_id)
            total_service_income_m = cache.get(str(buss_id) + 's_d_r_t_m-total')
            cash_service_income_m = cache.get(str(buss_id) + 's_d_r_t_m-cash')
            credit_service_income_m = cache.get(str(buss_id) + 's_d_r_t_m-credit')
            services_income_this_month = cache.get(str(buss_id) + 's_d_r_t_m-income_this_month')

            if (not total_service_income_m and not cash_service_income_m and not credit_service_income_m
                    and not services_income_this_month):
                total_service_income_m, cash_service_income_m, credit_service_income_m, services_income_this_month = (
                    services_daily_records_this_month(buss_id))

            # daily_expenses_this_month
            daily_expenses_this_month.delay(buss_id)
            total_expense_m = cache.get(str(buss_id) + 'd_e_t_m-total')
            cash_expense_m = cache.get(str(buss_id) + 'd_e_t_m-cash')
            credit_expense_m = cache.get(str(buss_id) + 'd_e_t_m-credit')
            daily_expenses_record_m = cache.get(str(buss_id) + 'd_e_t_m-daily_totals')
            suppliers_m = cache.get(str(buss_id) + 'd_e_t_m-suppliers_m')
            expenses_this_month = cache.get(str(buss_id) + 'd_e_t_m-expenses_this_month')

            if (not total_expense_m and not cash_expense_m and not credit_expense_m and not daily_expenses_record_m
                    and not expenses_this_month):
                (total_expense_m, cash_expense_m, credit_expense_m, daily_expenses_record_m, suppliers_m,
                 expenses_this_month) = (daily_expenses_this_month(buss_id))

            if content.Choice == 'This Year':
                expense_record = monthly_expense_record_y
                total_expenses = total_expenses_y
                try:
                    total_income = total_product_income_y + total_service_income_y
                except Exception as e:
                    print(f'business-this_month{e}')
                    return redirect('/business/')
                """
                    make a dictionary from monthly service and product sales. 
                """
                for m, s in service_income_this_year.items():
                    for m_, p in products_income_this_year.items():
                        if m == m_:
                            for key, value in s.items():
                                if key == 'Amount':
                                    amount = value
                            for key, value in p.items():
                                if key == 'Amount':
                                    amount += value
                            for key, value in months.items():
                                if key == m:
                                    income_record[value] = amount

            elif content.Choice == 'This Month':
                expense_record = daily_expenses_record_m
                total_expenses = total_expense_m
                try:
                    total_income = total_product_income_m + total_service_income_m
                except Exception as e:
                    print(f'business-this_month{e}')
                    return redirect('/business/')
                """
                    make a dictionary from daily service and product sales this month. 
                """
                for d, s in services_income_this_month.items():
                    for d_, p in products_income_this_month.items():
                        if d == d_:
                            for key, value in s.items():
                                if key == 'Amount':
                                    amount = value
                            for key, value in p.items():
                                if key == 'Amount':
                                    amount += value
                            for key in range(1, 32):
                                if key == d:
                                    income_record[key] = amount

            delta = cash_account.Value - core_settings.Capital
            if delta < 1:
                delta *= -1
            try:
                delta_funds_percentage = round((delta / core_settings.Capital) * 100)
                delta_funds_percentage_remainder = 100 - delta_funds_percentage
                if delta_funds_percentage_remainder < 1:
                    delta_funds_percentage_remainder *= -1
            except ZeroDivisionError:
                delta_funds_percentage = 0
                delta_funds_percentage_remainder = 0

        (pending_invoices, pending_invoices_stats, processed_invoices, processed_invoices_stats, overdue_invoices,
         overdue_invoices_stats) = get_invoices(buss_id)

        if 'add_capital' in request.POST:
            amount = request.POST.get('Amount')
            pay_out_ratio = request.POST.get('pay_out_ratio')
            start_business_year = request.POST.get('start_business_year')
            if not amount:
                amount = 0
            amount = int(amount)

            if not pay_out_ratio:
                pay_out_ratio = 0
            pay_out_ratio = int(pay_out_ratio)
            pay_out_ratio_remainder = 100 - pay_out_ratio

            core_settings.Capital += amount
            core_settings.save()

            if start_business_year and not core_settings.StartBusinessYear:
                core_settings.StartBusinessYear = start_business_year
                core_settings.save()
                date_format = "%Y-%m-%d"
                start_ = datetime.strptime(core_settings.StartBusinessYear, date_format)
                start = start_ + timedelta(days=365)
                tax_this_year = TaxYear(Business=buss, TaxYearStart=core_settings.StartBusinessYear,
                                        TaxYearEnd=start)
                tax_this_year.save()

                tax_accounts = TaxAccount.objects.filter(Business__id=buss_id)
                for a in tax_accounts:
                    TaxAccountThisYear(TaxAccount=a, TaxYear=tax_this_year, AccumulatedTotal=0).save()

            elif start_business_year and core_settings.StartBusinessYear:
                if start_business_year != core_settings.StartBusinessYear:
                    core_settings.StartBusinessYear = start_business_year
                    core_settings.save()
                    try:
                        tax_this_year = TaxYear.objects.get(Business__id=buss_id,
                                                            TaxYearStart__lt=core_settings.StartBusinessYear)
                        tax_this_year.TaxYearStart = core_settings.StartBusinessYear
                        tax_this_year.save()
                    except TaxYear.DoesNotExist:
                        TaxYear(Business=buss, TaxYearStart=core_settings.StartBusinessYear,
                                TaxYearEnd=CoreSettings.objects.get(Business__id=buss_id).StartBusinessYear+timedelta(days=365)).save()

            cash_account.Value += amount
            cash_account.PayoutRatio = pay_out_ratio
            cash_account.save()

            return redirect('/business/')

        if 'search' in request.POST:
            search_item = request.POST.get('search')
            search_result = find_user(search_item)

            if not search_result:
                messages.error(request, 'This User does not Exist')

        if 'content' in request.POST:
            content_choice = request.POST.get('content_choice')
            content.Choice = content_choice
            content.save()

            return redirect('/business/')

    except Business.DoesNotExist:
        return redirect('/edit_business_profile/')

    context = {
        'buss': buss_id,
        'tax_this_year': tax_this_year,
        'search_result': search_result,
        'core_settings': core_settings,
        'start_date': start_date,
        'cash_account': cash_account,
        'content': content,
        'total_income': total_income,
        'total_expenses': total_expenses,
        "total_debt": total_debt,
        "total_credit": total_credit,
        "paid_for": paid_for,
        "income_in_hand": income_in_hand,
        "income_record": income_record,
        "expense_record": expense_record,
        "net_profit": net_profit,
        "profit_perc": profit_perc,
        "pay_out_ratio_remainder": pay_out_ratio_remainder,
        'delta_funds_percentage': delta_funds_percentage,
        "delta_funds_percentage_remainder": delta_funds_percentage_remainder,
        "total_dividends": total_dividends,
        'dividends': dividends,
        'retained_earnings': retained_earnings,
        'pending_invoices_stats': pending_invoices_stats,
        'processed_invoices_stats': processed_invoices_stats,
        'overdue_invoices_stats': overdue_invoices_stats
    }
    return render(request, 'registration/business.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def business_profile(request, id=0):
    if id != 0:
        try:
            ini = Business.objects.get(pk=id)
        except Business.DoesNotExist:
            return HttpResponse("there was an error in processing the profile you're trying to access"
                                "please try refreshing your browser or contact developer if the problem perists")
    else:
        try:
            ini = Business.objects.get(Owner=request.user.id)
        except Business.DoesNotExist:
            return redirect('/edit_business_profile/')
    context = {
        'ini': ini,
    }
    return render(request, 'registration/businessProfile.html', context)


def form_data(request):
    photo = request.FILES.get('photo')
    name = request.POST.get('name')
    type = request.POST.get('type')
    about = request.POST.get('about')
    email = request.POST.get('email')
    contact1 = request.POST.get('contact1')
    contact2 = request.POST.get('contact2')
    address = request.POST.get('address')
    postbox = request.POST.get('postbox')
    city = request.POST.get('city')
    country = request.POST.get('country')
    zipcode = request.POST.get('zipcode')
    instagram = request.POST.get('instagram')
    facebook = request.POST.get('facebook')
    linkedin = request.POST.get('linkedin')

    """fail-safe because it doesn't save business profile 
    if contact2 doesn't have a value look for better solution"""
    if contact2:
        pass
    else:
        contact2 = None

    return (photo, name, type, about, address, email, contact1, contact2, address, postbox, city,
            country, zipcode, instagram, facebook, linkedin)


@login_required(login_url="/login/")
def edit_business_profile(request):
    bus_types = ['Groceries', 'School & Office supplies', 'Fashion(Apparel, shoes, Jewerly)',
                 'Cosmetics', 'Furniture', 'Home appliances', 'Consumer Electronics', 'Security & Safety',
                 'Cars, spare parts & accessories', 'Construction', 'Tools & Hardware', 'Farm equipment & chemicals',
                 'Health & Personal Care', 'Entertainment', 'Hotel and Lodging', 'Food & Beverages', 'Sports',
                 'Real Estate'
                 ]
    try:
        ini = Business.objects.get(Owner=request.user.id)

        if request.method == 'POST':
            (photo, name, type, about, address, email, contact1, contact2, address, postbox, city,
             country, zipcode, instagram, facebook, linkedin) = form_data(request)

            if photo:
                if ini.Photo != photo:
                    ini.Photo = photo

            if name:
                if ini.Name != name:
                    ini.Name = name

            if type:
                if ini.Type != type:
                    ini.Type = type

            if about:
                if ini.About != about:
                    ini.About = about

            if email:
                if ini.Email != email:
                    ini.Email = email

            if postbox:
                if ini.PostBox != postbox:
                    ini.PostBox = postbox

            if address:
                if ini.Address != address:
                    ini.Address = address

            if contact1:
                if ini.Contact1 != contact1:
                    ini.Contact1 = contact1

            if contact2:
                if ini.Contact2 != contact2:
                    ini.Contact2 = contact2

            if city:
                if ini.City != city:
                    ini.City = city

            if country:
                if ini.Country != country:
                    ini.Country = country

            if zipcode:
                if ini.ZipCode != zipcode:
                    ini.ZipCode = zipcode

            if instagram:
                if ini.Instagram != instagram:
                    ini.Instagram = instagram
            elif not instagram and ini.Instagram:
                ini.Instagram = None

            if facebook:
                if ini.Facebook != facebook:
                    ini.Facebook = facebook
            elif not facebook and ini.Facebook:
                ini.Facebook = None

            if linkedin:
                if ini.Linkedin != linkedin:
                    ini.Linkedin = linkedin
            elif not linkedin and ini.Linkedin:
                ini.Linkedin = None

            ini.save()

            return redirect('/business_profile/')
        context = {
            'ini': ini,
            'bus_types': bus_types
        }
    except Business.DoesNotExist:

        group = Group.objects.get(name='Business(Owner)')
        if request.method == 'POST':
            (photo, name, Type, about, address, email, contact1, contact2, address, postbox, city,
             country, zipcode, instagram, facebook, linkedin) = form_data(request)

            ini = {'Photo': photo, 'Name': name, 'Type': Type, 'About': about, 'Address': address, 'Email ': email,
                   'Contact1': contact1, 'Contact2': contact2, 'PostBox': postbox, 'City': city, 'Country': country,
                   'ZipCode': zipcode, 'Instagram': instagram, 'Facebook': facebook, 'Linkedin': linkedin}

            try:
                Business.objects.get(Name=name)
                messages.error(request, f'A user by the name {name} already exists, please chose a different name')

                context = {
                    'ini': ini
                }
            except Business.DoesNotExist:
                buss = Business(Owner=request.user, Photo=photo, Name=name, Type=Type, About=about, Email=email,
                                Contact1=contact1, Contact2=contact2, Address=address, PostBox=postbox,
                                City=city, Country=country, ZipCode=zipcode, Instagram=instagram,
                                Facebook=facebook, Linkedin=linkedin)

                request.user.groups.add(group)
                buss.save()
                TaxSettings(Business=buss, VATRate=16.5).save()
                CoreSettings(Business=buss, Capital=0).save()
                CashAccount(Business=buss, Value=0, PayoutRatio=20).save()
                TaxAccount(Business=buss, Name='VAT', Interval='Annually', Notes='').save()
                TaxAccount(Business=buss, Name='PAYE', Interval='Annually', Notes='').save()
                TaxAccount(Business=buss, Name='PRESUMPTIVE', Interval='Quarterly', Notes='').save()
                TaxAccount(Business=buss, Name='INCOME', Interval='Annually', Notes='').save()
                dep = Department(Business=buss, Name='Executive', Description='Decision making and Planning')
                dep.save()
                Employee(User=request.user, Business=buss, Department=dep, Duty=dep.Description, AccessLevel=group).save()
                ExpenseAccount(Business=buss, Cashier=request.user, Name='Salaries', Type='Payroll', Interval='Monthly',
                               AutoRecord=False, Notes='').save()
                return redirect('/business/')

        context = {
            'bus_types': bus_types
        }
    return render(request, 'registration/editBusinessProfile.html', context)


"""def income_tax_calculater(amount):
    balance = amount

    balance -= 150000
    if balance >= 350000:
        income_tax = 350000 * (25 / 100)
        balance -= 350000

        if balance >= 2050000:
            income_tax += 2050000 * (30 / 100)
            balance -= 2050000

            if balance >= 2500000:
                income_tax += balance * (35 / 100)
    else:
        income_tax = 0

    return income_tax"""


"""def presumptive_tax_calculater(total_sales):
    presumptive_tax = 0
    if total_sales < 4000000:
        pass
    elif 4000000 < total_sales <= 7000000:
        presumptive_tax = 110000
    elif 7000000 < total_sales <= 10000000:
        presumptive_tax = 170000
    elif 10000000 < total_sales <= 12500000:
        presumptive_tax = 225000

    return presumptive_tax"""


def make_installment(tax_year, year_account, amount):
    try:
        TaxInstallments(TaxAccountThisYear=year_account, Amount=amount).save()
        tax_year.TotalPaid += amount
        tax_year.save()
        return 'success'
    except Exception as e:
        return f'unable to make the installment because of {e}'


def taxes(request):
    change = 0
    paid = 0
    total_sales = 0
    total_vat = 0
    total_paid = 0
    total_tax = 0
    total_payments_to_employees = 0
    total_paye = 0
    presumptive_tax = 0
    income_tax = 0
    balance = 0
    taxes_this_year = {}
    installments = {}
    try:
        buss = Business.objects.get(Owner=request.user.id)

        core_settings = CoreSettings.objects.get(Business=buss)
        tax_settings = TaxSettings.objects.get(Business=buss)
        tax_accounts = TaxAccount.objects.filter(Business=buss)

        if tax_accounts:
            tax_account_count = tax_accounts.count()
        else:
            tax_account_count = 0

        this_tax_year = get_tax_year(buss)

        if this_tax_year:
            start = this_tax_year.TaxYearStart
            end = this_tax_year.TaxYearEnd

            (total_expense, total_credit, paid_for, operational_expense, payroll_expense, total_operational_expense,
             total_payroll_expense, total_discount, discounts) = expenses(buss, start, end)

            product_income, total_product_income, cog, total_product_vat, total_product_presumptive_tax =\
                product_revenue(buss, tax_settings, start, end)

            service_income, total_service_income, total_service_vat, total_service_presumptive_tax = (
                service_revenue(buss, tax_settings, start, end))

            total_debt = debt_total(buss, start, end)

            (total_sales, total_vat, total_presumptive_tax, gp, op, revenue_after_tax,
             net_profit, income_tax, profit_after_income_tax, profit_perc, income_in_hand) = \
                totals_and_profits(buss.id, start, end, tax_settings, total_debt, total_service_vat, total_product_vat,
                                   total_product_presumptive_tax, total_service_presumptive_tax, total_product_income,
                                   total_service_income, cog, total_expense)

            if tax_settings.ShowEstimates:
                if total_sales > 12500000 and tax_settings.IncludePresumptiveTax:
                    tax_settings.IncludePresumptiveTax = False
                    tax_settings.IncludeIncomeTax = True
                    tax_settings.save()

                if total_sales <= 12500000 and tax_settings.IncludeVAT:
                    tax_settings.IncludePresumptiveTax = True
                    tax_settings.IncludeVAT = False
                    tax_settings.IncludeIncomeTax = False
                    tax_settings.save()

                elif total_sales >= 25000000 and (tax_settings.IncludePresumptiveTax or tax_settings.IncludeIncomeTax):
                    tax_settings.IncludeVAT = True
                    tax_settings.save()

            # presumptive tax is paid on annual turnover if it is below 12,500,000
            if tax_settings.IncludePresumptiveTax:
                presumptive_tax = presumptive_tax_calculator(total_sales)
                total_tax += presumptive_tax

            # income tax is paid on profit if annual turnover exceeds 12,500,000
            # it is a final tax, no need for income tax
            if tax_settings.IncludeIncomeTax:
                income_tax = income_tax_calculator(net_profit)

            # vat is paid on annual turnover(revenue generated) if the turnover exceeds 25,000,000
            # you are also required to pay income tax
            if tax_settings.IncludeVAT:
                total_tax += total_vat

            # pay as you earn is paid on salaries, allowances and other taxable earnings
            if tax_settings.IncludePAYE:
                total_paye, total_payments_to_employees = total_salary_and_paye(buss.id, start, end)
                total_tax += total_paye

            balance = total_tax - paid

            if this_tax_year:
                for a in tax_accounts:

                    if a.Name == 'VAT':
                        if total_vat:
                            try:
                                vat_account_this_year = TaxAccountThisYear.objects.get(TaxAccount__id=a.id,
                                                                                       TaxYear=this_tax_year)
                                if vat_account_this_year.AccumulatedTotal != total_vat:
                                    vat_account_this_year.AccumulatedTotal = total_vat
                                    vat_account_this_year.save()
                            except TaxAccountThisYear.DoesNotExist:
                                vat_account_this_year = TaxAccountThisYear(TaxAccount=a, TaxYear=this_tax_year,
                                                                           AccumulatedTotal=total_vat)
                                vat_account_this_year.save()

                    if a.Name == 'PAYE':
                        try:
                            paye_account_this_year = TaxAccountThisYear.objects.get(TaxAccount__id=a.id, TaxYear=this_tax_year)
                            if paye_account_this_year.AccumulatedTotal != total_paye:
                                paye_account_this_year.AccumulatedTotal = total_paye
                                paye_account_this_year.save()
                        except TaxAccountThisYear.DoesNotExist:
                            paye_account_this_year = TaxAccountThisYear(TaxAccount=a, TaxYear=this_tax_year,
                                                                        AccumulatedTotal=total_vat)
                            paye_account_this_year.save()

                    if a.Name == 'INCOME':
                        try:
                            income_account_this_year = TaxAccountThisYear.objects.get(TaxAccount__id=a.id,
                                                                                      TaxYear=this_tax_year)
                            if income_account_this_year.AccumulatedTotal != income_tax:
                                income_account_this_year.AccumulatedTotal = income_tax
                                income_account_this_year.save()
                        except TaxAccountThisYear.DoesNotExist:
                            income_account_this_year = TaxAccountThisYear(TaxAccount=a, TaxYear=this_tax_year,
                                                                          AccumulatedTotal=total_vat)
                            income_account_this_year.save()

                    if a.Name == 'PRESUMPTIVE':
                        try:
                            presumptive_account_this_year = TaxAccountThisYear.objects.get(TaxAccount=a,
                                                                                           TaxYear=this_tax_year)
                            if presumptive_account_this_year.AccumulatedTotal != presumptive_tax:
                                presumptive_account_this_year.AccumulatedTotal = presumptive_tax
                                presumptive_account_this_year.save()
                        except TaxAccountThisYear.DoesNotExist:
                            presumptive_account_this_year = TaxAccountThisYear(TaxAccount=a, TaxYear=this_tax_year,
                                                                               AccumulatedTotal=total_vat)
                            presumptive_account_this_year.save()

                for a in tax_accounts:
                    try:
                        account_this_year = TaxAccountThisYear.objects.get(TaxAccount__id=a.id, TaxYear=this_tax_year)
                        account_installments = TaxInstallments.objects.filter(TaxAccountThisYear=account_this_year)

                        if account_installments:
                            for i in account_installments:
                                paid = i.Amount
                                total_paid += i.Amount
                            installments[account_this_year.TaxAccount.id] = account_installments
                        taxes_this_year[a] = {}
                        taxes_this_year[a]['Total'] = account_this_year.AccumulatedTotal
                        taxes_this_year[a]['Paid'] = paid
                        taxes_this_year[a]['Balance'] = account_this_year.AccumulatedTotal - paid
                        paid = 0

                    except TaxAccountThisYear.DoesNotExist:
                        TaxAccountThisYear(TaxAccount=a, TaxYear=this_tax_year, AccumulatedTotal=0).save()
                        taxes_this_year[a] = {'Total': None, 'Paid': None, 'Balance': None}

            if 'tax_settings' in request.POST:
                show_estimate = request.POST.get('show_estimate')
                include_vat = request.POST.get('include_vat')
                include_paye = request.POST.get('include_paye')
                include_presumptive_tax = request.POST.get('include_presumptive_tax')
                include_income_tax = request.POST.get('include_income_tax')
                vat_rate = request.POST.get('vat_rate')

                # evaluate these switches
                # remove them and replace with better ones if  needed or just remove them
                # check if changes are mirrored in the statements
                # continue to error messages view

                if show_estimate != 'on' and tax_settings.ShowEstimates:
                    tax_settings.ShowEstimates = False
                    change += 1
                elif show_estimate == 'on' and not tax_settings.ShowEstimates:
                    tax_settings.ShowEstimates = True
                    change += 1

                if include_vat != 'on' and tax_settings.IncludeVAT:
                    tax_settings.IncludeVAT = False
                    change += 1
                elif include_vat == 'on' and not tax_settings.IncludeVAT:
                    tax_settings.IncludeVAT = True
                    tax_settings.IncludeIncomeTax = True
                    change += 1

                if include_paye != 'on' and tax_settings.IncludePAYE:
                    tax_settings.IncludePAYE = False
                    change += 1
                elif include_paye == 'on' and not tax_settings.IncludePAYE:
                    tax_settings.IncludePAYE = True
                    change += 1

                if include_presumptive_tax != 'on' and tax_settings.IncludePresumptiveTax:
                    tax_settings.IncludePresumptiveTax = False
                    change += 1
                elif include_presumptive_tax == 'on' and not tax_settings.IncludePresumptiveTax:
                    tax_settings.IncludePresumptiveTax = True
                    if tax_settings.IncludeIncomeTax:
                        tax_settings.IncludeIncomeTax = False
                    change += 1

                if include_income_tax != 'on' and tax_settings.IncludeIncomeTax:
                    tax_settings.IncludeIncomeTax = False
                    change += 1
                elif include_income_tax == 'on' and not tax_settings.IncludeIncomeTax:
                    tax_settings.IncludeIncomeTax = True
                    if tax_settings.IncludePresumptiveTax:
                        tax_settings.IncludePresumptiveTax = False
                    change += 1
                if vat_rate:
                    if vat_rate != tax_settings.VATRate:
                        tax_settings.VATRate = vat_rate
                        change += 1

                tax_settings.save()
                if change == 1:
                    messages.success(request, 'change made successfully')
                elif change > 1:
                    messages.success(request, 'changes made successfully')

            if 'create_tax_account' in request.POST:
                name = request.POST.get('name')
                interval = request.POST.get('interval')
                notes = request.POST.get('notes')
                try:
                    TaxAccount.objects.get(Business=buss, Name=name)
                    messages.error(request, 'An account by this name already exists')
                except TaxAccount.DoesNotExist:
                    TaxAccount(Business=buss, Name=name, Interval=interval, Notes=notes).save()
                    messages.success(request, 'Account created successfully')

            if 'tax_installment' in request.POST:
                account_id = request.POST.get('account_id')
                installment_amount = request.POST.get('installment_amount')
                business_year = request.POST.get('business_year')
                account_id = int(account_id)
                installment_amount = int(installment_amount)
                if business_year == 'this year':
                    try:
                        tax_account_this_year = TaxAccountThisYear.objects.get(TaxAccount=account_id,
                                                                               TaxYear=this_tax_year)
                        installment = make_installment(this_tax_year, tax_account_this_year, installment_amount)
                        if installment == 'success':
                            messages.success(request, f'{tax_account_this_year.TaxAccount.Name} installment of '
                                                      f'{installment_amount} made for next year')
                        else:
                            messages.error(request, f'{installment}')
                    except TaxAccountThisYear.DoesNotExist:
                        messages.error(request, 'Unable to process tax account, please refresh the page')

                elif business_year == 'previous year':
                    try:
                        previous_tax_year = (TaxYear.objects.get
                                             (Business=buss,
                                              TaxYearStart=core_settings.StartBusinessYear - timedelta(days=366)))
                        try:
                            tax_account_previous_year = (TaxAccountThisYear.objects.get
                                                         (TaxAccount=account_id, TaxYear=previous_tax_year))

                            installment = make_installment(previous_tax_year, tax_account_previous_year,
                                                           installment_amount)
                            if installment == 'success':
                                messages.success(request, f'{tax_account_previous_year.TaxAccount.Name} installment of '
                                                          f'{installment_amount} made for next year')
                            else:
                                messages.error(request, f'{installment}')

                        except TaxAccountThisYear.DoesNotExist:
                            messages.error(request, 'Unable to process tax account for the previous year.')

                    except TaxYear.DoesNotExist:
                        messages.error(request, 'It seems this is your first business year.')

                elif business_year == 'next year':
                    for t in tax_accounts:
                        if t.id == account_id:
                            try:
                                next_tax_year = TaxYear.objects.get(Business=buss,
                                                                    TaxYearStart=this_tax_year.TaxYearEnd + timedelta(
                                                                        days=1))
                            except TaxYear.DoesNotExist:
                                next_tax_year = TaxYear(Business=buss,
                                                        TaxYearStart=this_tax_year.TaxYearEnd + timedelta(days=1),
                                                        TaxYearEnd=this_tax_year.TaxYearEnd + timedelta(days=366))
                                next_tax_year.save()

                            try:
                                tax_account_next_year = TaxAccountThisYear.objects.get(TaxAccount=account_id,
                                                                                       TaxYear=next_tax_year)
                            except TaxAccountThisYear.DoesNotExist:
                                tax_account = TaxAccount.objects.get(pk=account_id)
                                tax_account_next_year = TaxAccountThisYear(TaxAccount=tax_account, TaxYear=next_tax_year)
                                tax_account_next_year.save()
                            installment = make_installment(next_tax_year, tax_account_next_year, installment_amount)
                            if installment == 'success':
                                messages.success(request, f'{tax_account_next_year.TaxAccount.Name} installment of '
                                                          f'{installment_amount} made for next year')
                            else:
                                messages.error(request, f'{installment}')

    except Business.DoesNotExist:
        return redirect('/edit_business_profile/')

    context = {
        'tax_settings': tax_settings,
        'this_tax_year': this_tax_year,
        'total_sales': total_sales,
        'total_vat': total_vat,
        'total_paye': total_paye,
        'total_payments_to_employees': total_payments_to_employees,
        'total_tax': total_tax,
        'tax_accounts': tax_accounts,
        'taxes_this_year': taxes_this_year,
        'balance': balance,
        'total_paid': total_paid,
        'installments': installments,
        'tax_account_count': tax_account_count
    }
    return render(request, 'registration/taxes.html', context)
