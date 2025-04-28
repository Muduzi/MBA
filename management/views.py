import time

from django.shortcuts import render, redirect
from .models import *
from User.decorator import check_superuser
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.contrib import messages
from django.db.models import Q, Sum
from User.models import Business
from fuzzywuzzy import fuzz, process
from datetime import datetime, timedelta, timezone
from calendar import monthrange
from django.core.cache import cache
from celery import shared_task
from django.core import serializers
# Create your views here.


def get_plan_features_and_rem_features(plan_id):
    features = []
    plan_features = PlanFeatures.objects.filter(plan__id=plan_id)

    features_obj = Features.objects.all()
    if features_obj:
        for f in features_obj:
            features.append(f)

    for i in plan_features:
        if i in features:
            try:
                features.remove(i)
            except Exception as e:
                pass

    return features, plan_features


def get_plans_and_features():
    sub_plans = {}
    plans_and_features = {}

    plans = SubscriptionPlan.objects.all()

    features_obj = Features.objects.all()

    for i in plans:
        plan_feat = []
        sub_plans[i.id] = {'Name': i.Name, 'Price': i.Price}

        features = PlanFeatures.objects.filter(plan__id=i.id)
        for f in features:
            plan_feat.append(f.feature.Name)

        sub_plans[i.id]['features'] = plan_feat

        plans_and_features[i.id] = {'Name': i.Name, 'Price': i.Price, 'Features': plan_feat}

    return sub_plans, features_obj, plans_and_features


def performance_this_year():
    month = datetime.now(timezone.utc).month
    date = datetime.now(timezone.utc)
    m = 0
    overall_monthly_record = {}
    monthly_package_record = {}
    total_subscriptions_this_year = 0
    remainder = 100
    active_users_percentage = 0
    total_revenue = 0

    months = {1: 'Jan', 2: 'Feb', 3: 'March', 4: 'April', 5: 'May', 6: 'Jun',
              7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    subscription_plans = SubscriptionPlan.objects.all()

    while month != 0:
        month -= 1
        m += 1
        date_range = monthrange(datetime.now().year, m)
        start = datetime(date.year, m, 1)
        end = datetime(date.year, m, date_range[1])

        subs = Subscription.objects.filter(Start__range=(start, end), Status='Active')
        total = subs.aggregate(Sum('Plan__Price'))
        total = total['Plan__Price__sum']
        if not total:
            total = 0

        total_revenue += total

        count = subs.count()
        if not count:
            count = 0
        total_subscriptions_this_year += count
        overall_monthly_record[months[m]] = {'total':  total, 'count': count}

        monthly_package_record[months[m]] = {}
        for p in subscription_plans:
            sub = Subscription.objects.filter(Start__range=(start, end), Status='Active', Plan__id=p.id)
            total = sub.aggregate(Sum('Plan__Price'))
            total = total['Plan__Price__sum']
            if not total:
                total = 0
            count = sub.count()
            monthly_package_record[months[m]][p.Name] = {'total': total, 'count': count}

    active_users = Subscription.objects.filter(Status='Active').count()
    total_users = Business.objects.all().count()
    try:
        active_users_percentage = round((active_users/total_users)*100, 1)
    except ZeroDivisionError:
        pass

    remainder -= active_users_percentage
    average_percentages = {'average': active_users_percentage, 'remainder': remainder}

    # performance_this_year

    return total_revenue, average_percentages, overall_monthly_record, monthly_package_record


@shared_task()
def get_subscription_stats():
    active_businesses = 0
    inactive_businesses = 0
    upgrades = 0
    downgrades = 0
    maintaining = 0
    non_renewal = 0

    businesses = Business.objects.all()
    for b in businesses:
        try:
            active_plan = Subscription.objects.get(Business__id=b.id, Status='Active',
                                                   End__gte=datetime.now(timezone.utc).date())
            active_businesses += 1
        except Subscription.DoesNotExist:
            inactive_businesses += 1
            active_plan = None

        if active_plan:
            history = Subscription.objects.filter(Business__id=b.id, pk__gte=active_plan.id - 1).order_by('id')[:2]

            if len(history) > 1:
                if history[0].Plan.Price > history[1].Plan.Price:
                    downgrades += 1
                elif history[0].Plan.Price < history[1].Plan.Price:
                    upgrades += 1
                else:
                    maintaining += 1
        else:
            non_renewal += 1

    businesses_count = businesses.count()
    try:
        upgrades_percentage = round((upgrades / businesses_count) * 100)
        downgrades_percentage = round((downgrades / businesses_count) * 100)
        maintaining_percentage = round((maintaining / businesses_count) * 100)
        non_renewal_percentage = round((non_renewal / businesses_count) * 100)
    except ZeroDivisionError:
        upgrades_percentage = 0
        downgrades_percentage = 0
        maintaining_percentage = 0
        non_renewal_percentage = 0
    subscription_stats = {'businesses_count': businesses_count, 'inactive_businesses': inactive_businesses,
                          'active_businesses': active_businesses, 'upgrades': upgrades,
                          'upgrades_percentage': upgrades_percentage, 'downgrades': downgrades,
                          'downgrades_percentage': downgrades_percentage, 'maintaining': maintaining,
                          'maintaining_percentage': maintaining_percentage, 'non_renewal': non_renewal,
                          'non_renewal_percentage': non_renewal_percentage}

    return subscription_stats


@login_required(login_url="/login/")
@check_superuser()
def manager(request):
    plans = SubscriptionPlan.objects.all()
    features = Features.objects.all()
    sub_plans, features_obj, pf_container = get_plans_and_features()
    active_customers = Subscription.objects.filter(Status='Active')

    total_revenue, average_percentages, overall_monthly_record, monthly_package_record = performance_this_year()

    subscription_stats = get_subscription_stats()

    businesses_count = subscription_stats['businesses_count']
    inactive_businesses = subscription_stats['inactive_businesses']
    active_businesses = subscription_stats['active_businesses']
    upgrades = subscription_stats['upgrades']
    upgrades_percentage = subscription_stats['upgrades_percentage']
    downgrades = subscription_stats['downgrades']
    downgrades_percentage = subscription_stats['downgrades_percentage']
    maintaining = subscription_stats['maintaining']
    maintaining_percentage = subscription_stats['maintaining_percentage']
    non_renewal = subscription_stats['non_renewal']
    non_renewal_percentage = subscription_stats['non_renewal_percentage']

    context = {
        'plans': plans,
        'features': features,
        'pf_container':  pf_container,
        'average_percentages': average_percentages,
        'overall_monthly_record': overall_monthly_record,
        'monthly_package_record': monthly_package_record,
        'active_customers': active_customers,
        'upgrades': upgrades,
        'upgrades_percentage': upgrades_percentage,
        'downgrades': downgrades,
        'downgrades_percentage': downgrades_percentage,
        'maintaining': maintaining,
        'maintaining_percentage': maintaining_percentage,
        'non_renewal': non_renewal,
        'non_renewal_percentage': non_renewal_percentage
    }
    return render(request, 'management/manager.html', context)


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


@login_required(login_url="/login/")
@check_superuser()
def subscriptions(request):
    search = {}

    active = Subscription.objects.filter(Status='Active').order_by('-End')
    pending = Subscription.objects.filter(Status='Pending').order_by('-End')

    subscription_stats = get_subscription_stats()

    businesses_count = subscription_stats['businesses_count']
    inactive_businesses = subscription_stats['inactive_businesses']
    active_businesses = subscription_stats['active_businesses']
    upgrades = subscription_stats['upgrades']
    upgrades_percentage = subscription_stats['upgrades_percentage']
    downgrades = subscription_stats['downgrades']
    downgrades_percentage = subscription_stats['downgrades_percentage']
    maintaining = subscription_stats['maintaining']
    maintaining_percentage = subscription_stats['maintaining_percentage']
    non_renewal = subscription_stats['non_renewal']
    non_renewal_percentage = subscription_stats['non_renewal_percentage']

    total_revenue, average_perc, overall_monthly_record, monthly_package_record = performance_this_year()

    if request.method == 'POST':
        print('working1')
        lookup_word = request.POST.get('lookup_word')

        search = query_item_by_letter(lookup_word)

    context = {
        'search': search,
        'active': active,
        'pending': pending,
        'businesses_count': businesses_count,
        'inactive_count': inactive_businesses,
        'active_count': active_businesses,
        'total_revenue': total_revenue,
        'upgrades': upgrades,
        'upgrades_percentage': upgrades_percentage,
        'downgrades': downgrades,
        'downgrades_percentage': downgrades_percentage,
        'maintaining': maintaining,
        'maintaining_percentage': maintaining_percentage,
        'non_renewal': non_renewal,
        'non_renewal_percentage': non_renewal_percentage
    }
    return render(request, 'management/subscriptions.html', context)


@login_required(login_url="/login/")
@check_superuser()
def subscriber(request, id=0):
    start = None
    delta = timedelta(days=31)

    bus = Business.objects.get(pk=id)
    history = Subscription.objects.filter(Business__id=bus.id).order_by('End')

    plans = SubscriptionPlan.objects.all()

    if request.method == 'POST':
        if 'newPlan' in request.POST:
            plan_id = request.POST.get('Plan_id')
            plan_id = int(plan_id)
            for i in plans:
                if i.id == plan_id:
                    existing = (Subscription.objects.filter(Q(Business=bus.id) & Q(End__gte=datetime.now()) &
                                                           Q(Status='Active') | Q(Status='Pending')).order_by('-id')[:1])
                    if existing.exists():
                        for e in existing:
                            start = e.End
                        end = start + delta

                        new_subscription = Subscription(Business=bus, Plan=i, Start=start, End=end, Status='Pending')
                        new_subscription.save()

                        messages.success(request, f"New plan {i.Name} has been successfully added and will start from"
                                                  f"{new_subscription.Start.date()} will end on {new_subscription.End.date()}")
                    else:
                        start = datetime.now()
                        end = start + delta
                        new_subscription = Subscription(Business=bus, Plan=i, Start=start, End=end, Status='Active')
                        new_subscription.save()

                        messages.success(request, f"New plan {i.Name} has been successfully added and will start from"
                                                  f"{new_subscription.Start.date()} will end on {new_subscription.End.date()}")
        if 'Renew' in request.POST:
            active_plan = (Subscription.objects.filter(Q(Business=bus.id) & Q(End__gte=datetime.now()) &
                                                       Q(Status='Active') | Q(Status='Inactive'))[:1])
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
                    new_subscription = Subscription(Business=bus, Plan=plan, Start=start, End=end, Status='Pending')
                    new_subscription.save()

                    messages.success(request, f"The current plan {plan.Name} which is ends on"
                                              f" {new_subscription.End.date()} has been successfully renewed")
            else:
                messages.error(request, f"No recent subscription found to renew")

        if 'lookup transaction' in request.POST:
            lookup_id = request.POST.get('lookup_id')
            look_type = request.POST.get('transaction_type')

            look_type = look_type.replace(' ', '%')
            return redirect(f'/transactionInformation/{look_type}/{lookup_id}/')

    context = {
        'bus': bus,
        'history': history,
        'plans': plans
    }
    return render(request, 'management/subscriber.html', context)


@login_required(login_url="/login/")
@check_superuser()
def subscription(request, id=0):
    old_plan = ''
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
                        messages.success(request, f"subscription upgraded successfully from {old_plan} to {sub.Plan.Name}")
                    elif i.Price == sub.Plan.Price:
                        messages.info(request, "You can't upgrade to the same subscription, please choose a higher plan")
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


@login_required(login_url="/login/")
@check_superuser()
def subscription_settings(request):
    edit_feature = None
    delete_feature = None
    f_id = None
    plan_options = ['Basic', 'Standard', 'Advanced', 'Premium']

    plans, features, plans_and_features = get_plans_and_features()
    if request.method == 'POST':
        if 'create plan' in request.POST:
            name = request.POST.get('name')
            price = request.POST.get('price')
            f_li = request.POST.getlist('features')
            price = int(price)
            f_li = [int(f) for f in f_li]

            try:
                plan = SubscriptionPlan(Name=name, Price=price)
                plan.save()
                messages.success(request, f'{name} added successfully')

                for f in f_li:
                    feature = Features.objects.get(pk=f)
                    try:
                        PlanFeatures.objects.get(plan=plan, feature__id=feature.id)
                    except PlanFeatures.DoesNotExist:
                        PlanFeatures(plan=plan, feature=feature).save()
            except Exception as e:
                messages.error(request, f'{e}')

            plans = get_plans_and_features()

        if 'add features' in request.POST:
            feature = request.POST.get('feature')

            try:
                Features.objects.get(Name=feature)
            except Features.DoesNotExist:
                Features(Name=feature).save()

        if 'delete feature' in request.POST:
            f_id = request.POST.get('delete feature')

            try:
                delete_feature = Features.objects.get(pk=int(f_id))
                messages.info(request, f"Delete  '{delete_feature.Name}' ?")
            except Exception as e:
                messages.error(request, f'{e}')

        if 'confirm delete' in request.POST:
            f_id = request.POST.get('confirm delete')
            try:
                Features.objects.get(pk=int(f_id)).delete()
                sub_plans, features, plans_and_features = get_plans_and_features()
                messages.success(request, 'feature deleted successfully')
            except Exception as e:
                messages.error(request, f'{e}')

        if "don't delete" in request.POST:
            delete_feature = None

        if 'edit feature' in request.POST:
            f_id = request.POST.get('edit feature')
            f_id = int(f_id)
            try:
                edit_feature = Features.objects.get(pk=f_id)
            except Features.DoesNotExist:
                messages.error(request, 'failed to get the feature')

        if 'edited feature' in request.POST:
            f_id = request.POST.get('edited feature')
            feature = request.POST.get('feature')
            f_id = int(f_id)
            try:
                edit_feature = Features.objects.get(pk=f_id)
                edit_feature.Name = feature
                edit_feature.save()
                print(f'edited feature{feature}')
                plans, features, plans_and_features = get_plans_and_features()
                edit_feature = None
                messages.success(request, 'feature edited successfully')
            except Features.DoesNotExist:
                messages.error(request, 'failed to get the feature')

        if 'cancel edit' in request.POST:
            edit_feature = None

    context = {
        'plans': plans,
        'plan_options': plan_options,
        'features': features,
        'plan_and_features': plans_and_features,
        'edit_feature': edit_feature,
        'delete_feature': delete_feature,
    }
    return render(request, 'management/subscriptionSettings.html', context)


def edit_plan(request, id=0):
    plan = None
    delete_feature = None
    plan_features = None
    features = None
    try:
        plan = SubscriptionPlan.objects.get(pk=id)

        features, plan_features = get_plan_features_and_rem_features(plan.id)
        if request.method == 'POST':
            if 'add features' in request.POST:
                new_features = request.POST.getlist('features')
                new_features = [int(f) for f in new_features]
                for f in new_features:
                    try:
                        feature = Features.objects.get(pk=f)

                        PlanFeatures(plan=plan, feature=feature).save()
                        features, plan_features = get_plan_features_and_rem_features(plan.id)
                    except Exception as e:
                        messages.error(request, f'{e}')

            if 'delete feature' in request.POST:
                f_id = request.POST.get('delete feature')

                try:
                    delete_feature = PlanFeatures.objects.get(plan__id=plan.id, feature__id=int(f_id))
                    messages.info(request, f"Delete  '{delete_feature.feature.Name}' ?")
                except Exception as e:
                    messages.error(request, f'here{e}')

            if 'confirm delete' in request.POST:
                f_id = request.POST.get('confirm delete')
                try:
                    PlanFeatures.objects.get(plan__id=plan.id, feature__id=int(f_id)).delete()
                    features, plan_features = get_plan_features_and_rem_features(plan.id)
                    messages.success(request, 'feature deleted successfully')
                except Exception as e:
                    messages.error(request, f'{e}')

            if "don't delete" in request.POST:
                delete_feature = None

    except Exception as e:
        messages.error(request, f'{e}')

    context = {
        'plan': plan,
        'plan_features': plan_features,
        'features': features,
        'delete_feature': delete_feature
    }
    return render(request, 'management/editPlan.html', context)
