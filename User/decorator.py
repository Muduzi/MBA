from django.http import HttpResponse
from django.shortcuts import redirect
from management.models import Subscription
from User.models import Business, Employee
from datetime import datetime, timedelta, timezone
from django.db.models import Q, Sum


def allowed_users(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            group = None
            access_denied = 'N-S-U00'
            if request.user.groups.exists():
                group = request.user.groups.all()[0].name
                if group in allowed_roles:
                    return view_func(request, *args, **kwargs)
                else:
                    return redirect(f"/Error/{access_denied}/")
            else:
                return redirect(f"/Error/{access_denied}/")
        return wrapper_func
    return decorator


def check_superuser():
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            not_a_super_user = 'N-S-U00'
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                """send me an email alert"""
                return redirect(f"/Error/{not_a_super_user}/")
        return wrapper_func
    return decorator


# filters active subscriptions, checks if end date is past due,
# if it is past due, it deactivates the plan then looks for pending plans if there's one activates and returns it
# if there are many activates the oldest

def get_active_subscription(buss_id):
    active = []
    current = Subscription.objects.filter(Business__id=buss_id, Status='Active').order_by('id')
    if current.exists():
        for c in current:
            if c.End >= datetime.now(timezone.utc):
                active.append(c)
            else:
                c.Status = 'Inactive'
                c.save()
        if len(active) > 1:
            for a in active[1:]:
                a.Status = 'Pending'
                a.save()
        return active[0].Plan.Name
    else:
        pending = Subscription.objects.filter(Business__id=buss_id, Status='Pending').order_by('id')
        if pending.exists():
            pending = pending[:1]
            pending.Status = 'Active'
            pending.save()
        else:
            return False


def check_active_subscription(allowed_subscriptions=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            no_active_subscription = 'A-S-N-F00'
            service_not_in_subscription = 'S-N-I-S00'
            no_business_association_found = 'B-P-A-E00'
            try:
                buss = Employee.objects.get(User__id=request.user.id).Business
                has_active_subscription = get_active_subscription(buss.id)
                if has_active_subscription:
                    if has_active_subscription in allowed_subscriptions:
                        return view_func(request, *args, **kwargs)
                    else:
                        return redirect(f"/Error/{service_not_in_subscription}/")
                else:
                    return redirect(f"/Error/{no_active_subscription}/")
            except Employee.DoesNotExist:
                try:
                    buss = Business.object.get(Owner__id=request.user.id)
                    has_active_subscription = get_active_subscription(buss.id)
                    if has_active_subscription:
                        if has_active_subscription in allowed_subscriptions:
                            return view_func(request, *args, **kwargs)
                        else:
                            return redirect(f"/Error/{service_not_in_subscription}/")
                except Business.DoesNotExist:
                    return redirect(f"/Error/{no_business_association_found}/")
        return wrapper_func
    return decorator
