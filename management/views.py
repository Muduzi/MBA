from django.shortcuts import render, redirect
from .models import *
from User.decorator import check_superuser
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.contrib import messages
from django.db.models import Q, Sum
from User.models import Business
from fuzzywuzzy import fuzz, process
from datetime import datetime, timedelta
from calendar import monthrange
# Create your views here.


def planFeatures():
    pf_container = {}
    pf_list = []
    all_features = []

    plans = SubscriptionPlan.objects.all()
    features = Features.objects.all()
    for f in features:
        all_features.append(f)
    for p in plans:
        pf_container[p.Name] = {}
        plan_features = PlanFeatures.objects.filter(plan=p.id)

        for pf in plan_features:
            pf_list.append(pf.feature)

        for f in all_features:
            if f in pf_list:
                pf_container[p.Name][f.Name] = "yes"
            else:
                pf_container[p.Name][f.Name] = None
        pf_list = []

    return pf_container


def planFeatures2():
    pf_container = {}
    pf_list = []

    plans = SubscriptionPlan.objects.all()

    for p in plans:
        pf_container[p.Name] = {}
        plan_features = PlanFeatures.objects.filter(plan=p.id)

        for pf in plan_features:
            pf_list.append(pf.feature)

        pf_container[p.Name] = pf_list

        pf_list = []

    return pf_container


def performance_this_year():
    month = datetime.now().month
    date = datetime.now()
    m = 0
    total = 0
    overall_monthly_record = {}
    count = 0
    monthly_package_record = {}
    average = 0
    average_perc = {}
    remainder = 100
    average_active_perc = 0
    packages = ['Bronze', 'Silver', 'Gold', 'Diamond', 'Platinum']

    for i in range(month):
        m += 1
        date_range = monthrange(datetime.now().year, m)
        start = datetime(date.year, m, 1)
        end = datetime(date.year, m, date_range[1])

        subs = Subscription.objects.filter(Start__range=(start, end), Status='Active')
        if subs:
            total = subs.aggregate(Sum('Plan__Price'))
            total = total['Plan__Price__sum']
            print('working')
            count = subs.count()
            average += count
        overall_monthly_record[m] = {}
        overall_monthly_record[m]['total'] = total
        overall_monthly_record[m]['count'] = count

        monthly_package_record[m] = {}
        for p in packages:
            sub = Subscription.objects.filter(Start__range=(start, end), Status='Active', Plan__Name=p)
            total = sub.aggregate(Sum('Plan__Price'))
            total = total['Plan__Price__sum']

            if not total:
                total = 0

            count = sub.count()
            monthly_package_record[m][p] = {}
            monthly_package_record[m][p]['total'] = total
            monthly_package_record[m][p]['count'] = count

    bus_count = Business.objects.all().count()
    try:
        average /= month
        average = round(average)
        average_active_perc = (average/bus_count*100)
    except ZeroDivisionError:
        pass

    remainder -= average_active_perc
    average_perc['average'] = average_active_perc
    average_perc['remainder'] = remainder
    print('==============================================================================================')
    print(bus_count)
    return average_perc, overall_monthly_record, monthly_package_record


@login_required(login_url="/login/")
@check_superuser()
def management_view(request):
    plans = SubscriptionPlan.objects.all()
    features = Features.objects.all()
    pf_container = planFeatures2()
    active_customers = Subscription.objects.filter(Status='Active')
    average_perc, overall_monthly_record, monthly_package_record = performance_this_year()

    (businesses_count, inactive, active_businesses, total_amount, upgrades, upgrades_perc, downgrades,
     downgrades_perc, maintaining, maintaining_perc, non_renewal, non_renewal_perc) = get_subscription_stats()
    context = {
        'plans': plans,
        'features': features,
        'pf_container':  pf_container,
        'average_perc': average_perc,
        'overall_monthly_record': overall_monthly_record,
        'monthly_package_record': monthly_package_record,
        'active_customers': active_customers,
        'upgrades': upgrades,
        'upgrades_perc': upgrades_perc,
        'downgrades': downgrades,
        'downgrades_perc': downgrades_perc,
        'maintaining': maintaining,
        'maintaining_perc': maintaining_perc,
        'non_renewal': non_renewal,
        'non_renewal_perc': non_renewal_perc
    }
    return render(request, 'management/management.html', context)

def subscriptionFeatures(plan):
    ft = {}
    f_li = []
    existing = []

    features = Features.objects.all()
    pf = PlanFeatures.objects.filter(plan=plan.id)

    for e in pf:
        existing.append(e.feature)

    for f in features:
        f_li.append(f)

    for f in f_li:
        if f in existing:
            ft[f] = "yes"
        else:
            ft[f] = None

    return features, existing, ft


@login_required(login_url="/login/")
@check_superuser()
def addfeature(request, id=0):
    ft = {}
    try:
        plan = SubscriptionPlan.objects.get(pk=id)

        features, existing, ft = subscriptionFeatures(plan)

        if request.method == 'POST':
            print('working1')
            if plan.Name in request.POST:
                for f in features:
                    check = request.POST.get(f.Name)
                    print(check)
                    print('working2')
                    if check:
                        if f in existing:
                            pass
                        else:
                            pf = PlanFeatures(plan=plan, feature=f)
                            pf.save()

                            features, existing, ft = subscriptionFeatures(plan)

                            messages.success(request, 'feature added successfully')
                    else:
                        if f in existing:
                            PlanFeatures.objects.get(feature=f).delete()

                            features, existing, ft = subscriptionFeatures(plan)

                            messages.info(request, 'feature removed successfully')

    except SubscriptionPlan.DoesNotExist:
        messages.error(request, 'failed to add feature')
    context = {
        'plan': plan,
        'features': features,
        'ft': ft
    }
    return render(request, 'management/addfeature.html', context)


def query_item_by_letter(lookup_word):
    """
    search1 = Products.objects.filter(Q(name__icontains=lookup_word))
    search2 = Categories.objects.filter(Q(name__icontains=lookup_word))
    """
    match = []
    lookup1 = Business.objects.all()
    for i in lookup1:
        ratio = fuzz.partial_ratio(lookup_word.lower(), i.Name.lower())

        if ratio > 60:
            if i.Photo:
                photo = i.Photo
            else:
                photo = None

            match.append({'id': i.id, 'name': i.Name, 'photo': photo, 'ratio': ratio})
    search = sorted(match, key=lambda x: x['ratio'], reverse=True)
    print(match)
    return search

def get_subscription_stats():
    inactive = {}
    businesses_count = 0
    active_businesses = 0
    total_amount = 0
    upgrades = 0
    upgrades_perc = 0
    downgrades = 0
    downgrades_perc = 0
    maintaining = 0
    maintaining_perc = 0
    non_renewal = 0
    non_renewal_perc = 0
    subs_li = []
    businesses = Business.objects.all()
    businesses_count += businesses.count()

    for b in businesses:
        try:
            sub = Subscription.objects.get(Business=b.id, Status='Active')

            active_businesses += 1
            total_amount += sub.Plan.Price
            subs = Subscription.objects.filter(Business=b.id).order_by('-End')[:2]

            if len(subs_li) <= 2:
                for s in subs:
                    subs_li.append(s)

            if subs_li[0].Plan.Price > subs_li[1].Plan.Price:
                upgrades += 1

            elif subs_li[0].Plan.Price < subs_li[1].Plan.Price:
                downgrades += 1

            else:
                maintaining += 1
            subs_li = []
        except Subscription.DoesNotExist:
            inactive[b.id] = b
            non_renewal += 1

    try:
        upgrades_perc = (upgrades/active_businesses*100)
        upgrades_perc = round(upgrades_perc)
    except ZeroDivisionError:
        pass

    try:
        downgrades_perc = (downgrades/active_businesses*100)
        downgrades_perc = round(downgrades_perc)
    except ZeroDivisionError:
        pass

    try:
        maintaining_perc = (maintaining/active_businesses*100)
        maintaining_perc = round(maintaining_perc)
    except ZeroDivisionError:
        pass

    try:
        non_renewal_perc = (non_renewal/businesses_count*100)
        non_renewal_perc = round(non_renewal_perc)
    except ZeroDivisionError:
        pass

    return (businesses_count, inactive, active_businesses, total_amount, upgrades, upgrades_perc, downgrades,
            downgrades_perc, maintaining, maintaining_perc, non_renewal, non_renewal_perc)


@login_required(login_url="/login/")
@check_superuser()
def subscriptions(request):
    search = {}

    (businesses_count, inactive, active_businesses, total_amount, upgrades, upgrades_perc, downgrades,
     downgrades_perc, maintaining, maintaining_perc, non_renewal, non_renewal_perc) = get_subscription_stats()

    active = Subscription.objects.filter(Status='Active').order_by('-End')
    pending = Subscription.objects.filter(Status='Pending').order_by('-End')

    if request.method == 'POST':
        print('working1')
        lookup_word = request.POST.get('lookup_word')

        search = query_item_by_letter(lookup_word)

    context = {
        'search': search,
        'active': active,
        'pending': pending,
        'businesses_count': businesses_count,
        'inactive': inactive,
        'active_businesses': active_businesses,
        'total_amount': total_amount,
        'upgrades': upgrades,
        'upgrades_perc': upgrades_perc,
        'downgrades': downgrades,
        'downgrades_perc': downgrades_perc,
        'maintaining': maintaining,
        'maintaining_perc': maintaining_perc,
        'non_renewal': non_renewal,
        'non_renewal_perc': non_renewal_perc
    }
    return render(request, 'management/subscriptions.html', context)


@login_required(login_url="/login/")
@check_superuser()
def addSubscription(request, id=0):
    delta = timedelta(days=31)
    bus = Business.objects.get(pk=id)
    history = Subscription.objects.filter(Business=bus.id).order_by('End')
    plans = SubscriptionPlan.objects.all()

    if request.method == 'POST':
        if 'newPlan' in request.POST:
            plan = request.POST.get('Plan')

            for i in plans:
                if i.Name == plan:
                    existing = (Subscription.objects.filter(Q(Business=bus.id) & Q(End__gte=datetime.now()) &
                                                           Q(Status='Active') | Q(Status='Pending')).order_by('-id')[:1])
                    if existing.exists():
                        for e in existing:
                            start = e.End
                        end = start + delta

                        newSubscription = Subscription(Business=bus, Plan=i, Start=start, End=end, Status='Pending')
                        newSubscription.save()

                        messages.success(request, f"New plan {i.Name} has been successfully added and will start from"
                                                  f"{newSubscription.Start.date} will end on {newSubscription.End.date}")
                    else:
                        start = datetime.now()
                        end = start + delta
                        newSubscription = Subscription(Business=bus, Plan=i, Start=start, End=end, Status='Active')
                        newSubscription.save()

                        messages.success(request, f"New plan {i.Name} has been successfully added and will start from"
                                                  f"{newSubscription.Start.date} will end on {newSubscription.End.date}")
        if 'Renew' in request.POST:
            active_plan = (Subscription.objects.filter(Q(Business=bus.id) & Q(End__gte=datetime.now()) &
                                                      Q(Status='Active')| Q(Status='Inactive'))[:1])
            if active_plan.exists():
                pending_plan = Subscription.objects.filter(Business=bus.id, Status='Pending')
                if pending_plan.exists():
                    """if there are pending plans their starts and ends will be pushed by 31 days to accommodate the
                     renewed plan"""
                    for pp in pending_plan:
                        pp.Start += delta
                        pp.End += delta
                        pp.save()
                        print("working")

                for ap in active_plan:
                    start = ap.End
                    end = start+delta
                    plan = ap.Plan
                    newSubscription = Subscription(Business=bus, Plan=plan, Start=start, End=end, Status='Pending')
                    newSubscription.save()

                    messages.success(request, f"The current plan {plan.Name} which is ends on"
                                              f" {newSubscription.End.date} has been successfully renewed")
            else:
                messages.error(request, f"No recent subscription found to renew")
    context = {
        'bus': bus,
        'history': history,
        'plans': plans
    }
    return render(request, 'management/subscriber.html', context)


@login_required(login_url="/login/")
@check_superuser()
def subscription(request, id=0):
    sub = Subscription.objects.get(pk=id)
    bus = Business.objects.get(pk=sub.Business.id)
    plans = SubscriptionPlan.objects.all()

    if request.method == 'POST':
        if 'upgrade' in request.POST:
            plan = request.POST.get('Plan')

            for i in plans:
                if i.Name == plan:
                    if i.Price > sub.Plan.Price:
                        sub.Plan = i
                        sub.save()
                        messages.success(request, f"subscription upgraded successfully from {plan} to {sub.Plan}")
                    else:
                        messages.error(request, "subscription downgrades are not allowed")

        if 'deactivate' in request.POST:
            sub.Status = 'Inactive'
            sub.save()
            messages.success(request, 'subscription deactivated successfully')

        if 'activate' in request.POST:
            try:
                Subscription.objects.get(Business=bus, Status='Active')
                messages.error(request, "The user already has an active subscription")
            except Subscription.DoesNotExists:
                if sub.Status == 'Pending':
                    sub.Status = 'Active'
                    sub.save()
                    messages.success(request, 'subscription activated successfully')

                elif sub.Status == 'Inactive':
                    if sub.End < datetime.now():
                        sub.Status = 'Active'
                        sub.save()

                        messages.success(request, 'subscription activated successfully')

                    else:
                        messages.error(request, 'maximum number of days for the subscription reached')

    context = {
        'bus': bus,
        'sub': sub,
        'plans': plans
    }
    return render(request, 'management/subscription.html', context)

