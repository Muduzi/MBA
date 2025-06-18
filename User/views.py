import time

from django.shortcuts import (render, redirect, HttpResponse)
from django.contrib.auth.models import User, Group
from django.contrib import messages
from User.models import (Profile, Department, Business, Employee, Salary, EmployeeAllowance, Allowance,
                         EmployeeIncentives)
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from User.decorator import allowed_users
from django.db.models import Sum, Q
from datetime import datetime, timezone
from calendar import monthrange
from User.models import CashAccount
from expenses.models import Expense, ExpenseAccount
from .business import income_tax_calculater
from User.models import TaxSettings, TaxAccount, TaxAccountThisYear, TaxYear
from .business import get_tax_year
from itertools import chain
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from income.invoice import date_initial
from management.views import pay_as_you_earn_calculator
# Create your views here.


def login_view(request):

    if request.method == 'POST':
        if 'login' in request.POST:
            name = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=name, password=password)
            if user:
                login(request, user)
                return redirect('/')
            else:
                messages.error(request, 'Enter a valid username and password!')

    context = {
    }
    return render(request, 'registration/login.html', context)


def sign_up(request):
    if request.method == 'POST':
        if 'signup' in request.POST:
            username = request.POST.get('username')
            firstname = request.POST.get('first name')
            lastname = request.POST.get('last name')
            email = request.POST.get('email')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            if password1 == password2:
                try:
                    u = User.objects.get(username=username)
                    messages.error(request, f'A user by this name {u.username} already exists!')
                except User.DoesNotExist:
                    new_user = User.objects.create_user(username=username, first_name=firstname, last_name=lastname,
                                                        email=email, password=password2)
                    new_user.save()

                    new_profile = Profile(User=new_user)
                    new_profile.save()

                    user = authenticate(request, username=username, password=password2)
                    login(request, user)

                    return redirect('/profile_form/')

            else:
                messages.error(request, 'passwords do not match')
    context = {

    }
    return render(request, 'registration/signUp.html', context)


@login_required(login_url="/login/")
def logout_view(request):
    if request.method == 'POST':
        if 'cancel' in request.POST:
            return redirect('/')
        if 'confirm' in request.POST:
            logout(request)
            return redirect('/')
    context = {

    }
    return render(request, 'registration/logout.html', context)


@login_required(login_url="/login/")
def management(request):
    if request.method == "POST":
        if "refresh cache" in request.POST:
            cache.clear()
    context = {

    }
    return render(request, 'registration/management.html', context)


@login_required(login_url="/login/")
def profile_form(request):
    date = '0000-00-00'
    try:
        user_obj = request.user
        prof = Profile.objects.get(User=user_obj)

        if prof.DOB:
            date = date_initial(prof.DOB)

        if request.method == 'POST':
            username = request.POST.get('username')
            photo = request.FILES.get('photo')
            dob = request.POST.get('dob')
            gender = request.POST.get('gender')
            role = request.POST.get('role')
            about = request.POST.get('about')
            contact1 = request.POST.get('contact1')
            contact2 = request.POST.get('contact2')
            instagram = request.POST.get('instagram')
            facebook = request.POST.get('facebook')
            linkedin = request.POST.get('linkedin')
            city = request.POST.get('city')
            country = request.POST.get('country')

            if username:
                if user_obj.username != username:
                    user_obj.username = username
                    user_obj.save()
            elif not username and user_obj.username:
                messages.error(request, 'username field can not be blank')

            if dob:
                if prof.DOB != dob:
                    prof.DOB = dob
            elif not dob and prof.DOB:
                messages.error(request, 'date of birth field can not be blank')

            if gender:
                if prof.Gender != gender:
                    prof.Gender = gender
            elif not gender and prof.Gender:
                messages.error(request, 'Gender field can not be blank')

            if photo:
                if prof.Photo != photo:
                    prof.Photo = photo
            elif not photo and prof.Photo:
                messages.error(request, 'photo field can not be blank')

            if about:
                if prof.About != about:
                    prof.About = about
            elif not about and prof.About:
                prof.About = None

            if contact1:
                if prof.Contact1 != contact1:
                    prof.Contact1 = contact1
            elif not contact1 and prof.Contact1:
                messages.error(request, 'contact1 field can not be blank')

            if contact2:
                if prof.Contact2 != contact2:
                    prof.Contact2 = contact2
            elif not contact2 and prof.Contact2:
                prof.Contact2 = None

            if city:
                if prof.City != city:
                    prof.City = city

            if country:
                if prof.Country != country:
                    prof.Country = country

            if instagram:
                if prof.Instagram != instagram:
                    prof.Instagram = instagram
            elif not instagram and prof.Instagram:
                prof.Instagram = None

            if facebook:
                if prof.Facebook != facebook:
                    prof.Facebook = facebook
            elif not facebook and prof.Facebook:
                prof.Facebook = None

            if linkedin:
                if prof.Linkedin != linkedin:
                    prof.Linkedin = linkedin
            elif not linkedin and prof.Linkedin:
                prof.Linkedin = None

            prof.save()

    except Profile.DoesNotExist:
        return HttpResponse("unable to find user profile")
    context = {
        'profile': prof,
        'date': date,
    }
    return render(request, 'registration/profileForm.html', context)


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def departments_view(request):
    number = 0
    employees_count = 0
    departments = {}
    try:
        buss = Business.objects.get(Owner=request.user.id)

        g = Group.objects.all()
        dep_table = Department.objects.filter(Business=buss.id)

        g = Group.objects.filter()

        if dep_table.exists():
            employees_count = Employee.objects.filter(Business=buss).count()
            print('emp_count', employees_count)
            for d in dep_table:
                number = Employee.objects.filter(Business=buss, Department=d).count()
                departments[d.id] = {'Name': d.Name, 'Head': d.Head, 'Description': d.Description, 'count':  number}
                number = 0

        if 'save' in request.POST:
            name = request.POST.get('name')
            head = request.POST.get('head')
            description = request.POST.get('description')
            head = int(head)
            try:
                head = Employee.objects.get(pk=head)
                try:
                    buss = Business.objects.get(Owner=request.user.id)
                    check = Department.objects.filter(Business=buss.id, Name=name)
                    if check.exists():
                        return HttpResponse('A department by that name already exists')
                    else:
                        new_dep = Department(Business=buss, Name=name, Description=description, Head=head)
                        new_dep.save()
                        return redirect('/departments/')
                except Business.DoesNotExist:
                    return HttpResponse('You are not authorized to make changes to the department info!')
            except Business.DoesNotExist:
                return HttpResponse('trouble processing this employee profile!')
    except Business.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'departments': departments,
        'g': g,
        'employees_count': employees_count
    }
    return render(request, 'registration/departments.html', context)


def find_user(search_item):
    search_result = User.objects.filter(Q(username__contains=search_item) | Q(first_name__contains=search_item) |
                                        Q(last_name__contains=search_item))
    return search_result


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def department_view(request, id=0):
    employee_count = 0
    search_result = None
    paye_account_this_year = None

    try:
        buss = Business.objects.get(Owner=request.user.id)
        this_tax_year = get_tax_year(buss)
        groups = Group.objects.all()

        tax_settings = TaxSettings.objects.get(Business=buss)
        tax_accounts = TaxAccount.objects.filter(Business=buss)

        department = Department.objects.get(Business=buss.id, pk=id)
        employees = Employee.objects.filter(Business=buss.id, Department=department)
        if employees:
            employee_count = employees.count()

        cash_account = CashAccount.objects.get(Business=buss)

        if request.method == 'POST':
            if 'edit' in request.POST:
                name = request.POST.get('name')
                head = request.POST.get('head')
                description = request.POST.get('description')
                head = int(head)

                if name:
                    if name != department.Name:
                        department.Name = name

                if head:
                    if department.Head:
                        if head != department.Head.id:
                            for e in employees:
                                if head == e.User.id:
                                    department.Head = e.User
                    else:
                        for e in employees:
                            if head == e.User.id:
                                department.Head = e.User

                if description:
                    if description != department.Description:
                        department.Notes = description

                department.save()

                return redirect(f'/department/{id}/')

            if 'pay_salaries' in request.POST:
                if this_tax_year:
                    for a in tax_accounts:
                        if a.Name == 'PAYE':
                            try:
                                paye_account_this_year = TaxAccountThisYear.objects.get(TaxAccount=a,
                                                                                        TaxYear=this_tax_year)
                            except TaxAccountThisYear.DoesNotExist:
                                pass

                m = datetime.now().month
                y = datetime.now().year
                date_range = monthrange(y, m)
                start = datetime(y, m, 1)
                end = datetime(y, m, date_range[1])

                try:
                    Salary.objects.get(Employee__Department=department.id, Date__range=(start, end))
                    messages.error(request, f"Salaries have already been paid to the '{department.Name}' "
                                            f"department for this month")
                except Salary.DoesNotExist:
                    total_salaries = employees.aggregate(Sum('Salary'))
                    total_salaries = total_salaries['Salary__sum']
                    if not total_salaries:
                        total_salaries = 0

                    if total_salaries >= cash_account.Value:
                        messages.error(request, 'Not enough money in the cash account to pay employees')

                    else:
                        for i in employees:
                            try:
                                salary = Salary(TaxAccountThisYear=paye_account_this_year, Employee=i, Amount=i.Salary)
                                salary.save()

                                cash_account.Value -= total_salaries
                                cash_account.save()

                                note = f'Salary paid to {i.User.get_full_name()}, {department.Name} department'

                                try:
                                    expense_account = ExpenseAccount.objects.get(Business=buss, Name='Salaries')
                                except ExpenseAccount.DoesNotExist():
                                    expense_account = ExpenseAccount(Business=buss, Cashier=request.user,
                                                                     Name='Salaries', Type='Payroll',
                                                                     Interval='Monthly', AutoRecord=False,
                                                                     Notes='')
                                    expense_account.save()

                                e = Expense(Business=buss, Cashier=request.user, ExpenseAccount=expense_account,
                                            Salary=salary, Name='Salary', Price=total_salaries, Type="Payroll",
                                            Quantity=1, PMode='Cash', Notes=note)
                                e.save()

                                messages.success(request, 'Salary payment record made successfully')
                            except Exception as e:
                                messages.error(request, f'{e}')

            if 'search' in request.POST:
                search_item = request.POST.get('search')

                search_result = find_user(search_item)

            if 'selected user' in request.POST:
                search_item = request.POST.get('search')
                user = request.POST.get('user')

                if search_item:
                    search_result = find_user(search_item)

                elif user:
                    purpose = 'register'
                    return redirect(f'/employee_form/{purpose}/{user}/{id}/')

    except Business.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')
    context = {
        'department': department,
        'employees': employees,
        'employee_count': employee_count,
        'buss': buss,
        'groups': groups,
        'ID': id,
        'search_result': search_result
    }
    return render(request, 'registration/department.html', context)


def process_employee_and_salary(request):
    position = request.POST.get('position')
    access_level = request.POST.get('access_level')
    salary = request.POST.get('salary')
    salary_interval = request.POST.get('salary_interval')
    duty = request.POST.get('duty')

    salary = int(salary)
    return position, access_level, salary, salary_interval, duty


@login_required(login_url="/login/")
@allowed_users(allowed_roles=['Business(Owner)', 'Business(Manager)'])
def employee_form(request, purpose='', id=0, ID=0):
    employee = None
    employee_allowance = None
    change = 0
    candidate = None
    profile = None

    salary_intervals = ['Monthly', 'Weekly', 'Daily', 'Hourly', 'Agreed Condition']
    allowance_intervals = ['Monthly', 'Weekly', 'Daily', 'Agreed Condition']
    try:
        buss = cache.get('user id:' + str(request.user.id))
        if not buss:
            buss = Business.objects.get(Owner=request.user.id)
            cache.set('user id:' + str(request.user.id), buss)

        groups = cache.get('groups')
        if not groups:
            groups = Group.objects.all().exclude(Q(name='Business') | Q(name='Buying'))
            cache.set('groups', groups)
        if purpose == 'edit':
            try:
                employee = cache.get('employee id:'+str(id))
                if not employee:
                    employee = Employee.objects.get(Business=buss, pk=id)
                    cache.set('employee id:'+str(id), employee)

                employee_allowance = cache.get('employee allowance' + str(employee.id))
                if not employee_allowance:
                    try:
                        employee_allowance = EmployeeAllowance.objects.filter(Employee=employee)
                        cache.set('employee allowance' + str(employee.id), employee_allowance)
                    except EmployeeAllowance.DoesNotExist:
                        employee_allowance = None

                if request.method == 'POST':
                    if 'save' in request.POST:
                        position, access_level, salary, salary_interval, duty = process_employee_and_salary(request)

                        if position:
                            if position != employee.Position:
                                employee.Position = position
                                change += 1
                        if duty:
                            if duty != employee.Duty:
                                employee.Duty = duty
                                change += 1
                        if employee.User != buss.Owner:
                            if access_level:
                                if access_level != employee.AccessLevel.Name:
                                    for g in groups:
                                        if g.Name == access_level:
                                            employee.AccessLevel = g
                                            change += 1
                        if salary:
                            if salary != employee.Salary:
                                employee.Salary = salary
                                change += 1
                        if salary_interval:
                            if salary_interval != employee.Interval:
                                employee.Interval = salary_interval
                                change += 1

                        employee.save()
                        cache.set('employee id:' + str(id), employee)

                        if change == 1:
                            messages.success(request, 'change to employee record made successfully')
                        elif change >= 1:
                            messages.success(request, 'change to employee record made successfully')

                    if 'delete' in request.POST:
                        if employee.User == buss.Owner:
                            pass
                        else:
                            employee.delete()
                        return redirect(f'/edit_staff/{id}/{ID}/')

                    if 'add_allowance' in request.POST:
                        name = request.POST.get('name')
                        interval = request.POST.get('interval')
                        amount = request.POST.get('amount')

                        EmployeeAllowance(Employee=employee, Name=name, Interval=interval, Amount=amount).save()
                        employee_allowance = EmployeeAllowance.objects.filter(Employee=employee)
                        cache.set('employee allowance' + str(employee.id), employee_allowance)
            except Employee.DoesNotExist:
                messages.error(request, 'failed to process the employees profile')
        elif purpose == 'register':
            try:
                candidate = User.objects.get(pk=id)
                try:
                    profile = Profile.objects.get(User=candidate)
                except Profile.DoesNotExist:
                    messages.error(request, 'The candidate does not have a profile set up')

                try:
                    employee = Employee.objects.get(Business=buss, User=candidate)
                    messages.error(request, 'This user is already registered as an employee')
                    time.sleep(5)
                    return redirect(f'/employee_form/edit/{employee.id}/{ID}/')

                except Employee.DoesNotExist:
                    department = Department.objects.get(pk=ID)
                    if 'save' in request.POST:
                        position, access_level, salary, salary_interval, duty = process_employee_and_salary(request)
                        try:
                            employee = Employee(Business=buss, User=candidate, Department=department, Position=position,
                                                AccessLevel=Group.objects.get(name=access_level), Duty=duty,
                                                Interval=salary_interval, Salary=salary)
                            employee.save()
                        except Exception as e:
                            messages.error(request, f'{e}')
                        paye = pay_as_you_earn_calculator(Salary)
                        messages.success(request, 'employee profile successfully made')
                        if paye != 0:
                            time.sleep(3)
                            messages.info(request, f"if PAYE tax is enabled you'll liable to paying {paye} in tax")
            except User.DoesNotExist:
                        messages.error(request, "Failed to precess candidate user's profile")

    except Business.DoesNotExist:
        return HttpResponse('You are not affiliated to any business, please register your business'
                            ' or ask your employer to register you to their business')

    context = {
        'buss': buss,
        'candidate': candidate,
        'profile': profile,
        'employee': employee,
        'employee_allowance': employee_allowance,
        'groups': groups,
        'ID': ID,
        'salary_intervals': salary_intervals,
        'allowance_intervals': allowance_intervals

    }
    return render(request, 'registration/employeeForm.html', context)


