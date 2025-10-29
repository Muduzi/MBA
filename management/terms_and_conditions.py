from django.shortcuts import redirect, render
from User.decorator import check_superuser
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from User.models import Business
from .models import TermAndConditionsAgreements


def terms_and_conditions_view(request, id=0):
    data = {}
    try:
        buss = Business.objects.get(pk=id)
        """while True:
            print('here')"""
        if request.method == 'POST':
            if 'yes' in request.POST:
                try:
                    TermAndConditionsAgreements(Business=buss).save()
                    return redirect('/business/')
                except Exception as e:
                    print(f'error(creating terms and conditions): {e}')
            elif 'no' in request.POST:
                return redirect('/market/')
    except Business.DoesNotExist:
        return redirect(request.META.get('HTTP_REFERER'))
    context = {
        'data': data
    }
    return render(request, 'management/termsAndConditions.html', context)