from django.conf import settings
from django import forms
from django.utils.translation import pgettext as _

import stripe

from .models import Customer
from .settings import PLAN_CHOICES
from .sync import sync_customer

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


class PlanForm(forms.Form):

    plan = forms.ChoiceField(choices=PLAN_CHOICES)


########### Begin SignupForm code
try:
    from .widgets import StripeWidget
except ImportError:
    StripeWidget = None

try:
    from allauth.account.utils import setup_user_email
    from allauth.account.forms import SetPasswordField
    from allauth.account.forms import PasswordField
except ImportError:
    setup_user_email, SetPasswordField, PasswordField = None, None, None


if StripeWidget and setup_user_email:

    class StripeSubscriptionSignupForm(forms.Form):

        password1 = SetPasswordField(label=_("Password"))
        password2 = PasswordField(label=_("Password (again)"))
        confirmation_key = forms.CharField(
            max_length=40,
            required=False,
            widget=forms.HiddenInput())
        stripe_token = forms.CharField(widget=forms.HiddenInput())
        plan = forms.ChoiceField(choices=PLAN_CHOICES)

        # Stripe nameless fields
        number = forms.CharField(max_length=20,
            widget=StripeWidget(attrs={"data-stripe": "number"})
        )
        cvc = forms.CharField(max_length=4, label=_("CVC"),
            widget=StripeWidget(attrs={"data-stripe": "cvc"}))
        exp_month = forms.CharField(max_length=2,
                widget=StripeWidget(attrs={"data-stripe": "exp-month"})
        )
        exp_year = forms.CharField(max_length=4,
                widget=StripeWidget(attrs={"data-stripe": "exp-month"})
        )

        def save(self, request):
            new_user = self.create_user()
            super(StripeSubscriptionSignupForm, self).save(new_user)
            setup_user_email(request, new_user, [])
            self.after_signup(new_user)
            return new_user

        def after_signup(self, user, **kwargs):
            try:
                customer, created = Customer.get_or_create(self.request.user)
                customer.update_card(self.cleaned_data("stripe_token"))
                customer.subscribe(self.cleaned_data["plan"])
            except stripe.StripeError as e:
                # handle error here
                pass


