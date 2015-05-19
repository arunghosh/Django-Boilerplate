from abc import abstractmethod

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models, transaction
from django.contrib import admin
from django import forms

from apps.utils.models import AbstractTimestampModel
import apps.utils.validators as v
from .models import User


GENDER_OPTS = (
  (0, "--"),
  (1, "Male"),
  (2, "Female"),
  (3, "Other"),
)


class AbstractUserProfile(AbstractTimestampModel):
    user = models.OneToOneField(User, related_name="%(class)s_profile", null=True, blank=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    email = models.CharField(max_length=128)
    mobile = models.CharField(max_length=64, null=True, blank=True, validators = v.mobile.validators)
    address = models.CharField(max_length=512, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True)
    gender = models.PositiveSmallIntegerField(choices=GENDER_OPTS, default=0, verbose_name="Gender")
    dob = models.DateField(null=True, blank=True)

    def add_log(self):
        return self.user.add_log()

    @property
    def name(self):
        return self.first_name + " " + self.last_name

    @transaction.atomic
    def save(self, *args, **kwargs):
        super(AbstractUserProfile, self).save(*args, **kwargs)
        self._upsert_user(*args, **kwargs)

    def _upsert_user(self, *args, **kwargs):
        if not self.user:
            self.user = User.objects.create_user(
                email=self.email, 
                first_name=self.first_name, 
                last_name=self.last_name,
                password='abcd1234')
            super(AbstractUserProfile, self).save(*args, **kwargs)
        self.user.first_name = self.first_name
        self.user.last_name = self.last_name
        self.user.email = self.email
        self.user.save()

    class Meta:
        abstract = True


class AbstractRegistrationForm(forms.Form):

    submit_button_name = 'Register'

    first_name = forms.CharField(label=_('First Name'))
    last_name = forms.CharField(label=_('Last Name'))
    email = forms.EmailField()
    email_confirm = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        self.custom_errors = []
        super(AbstractRegistrationForm, self).__init__(*args, **kwargs)

    @abstractmethod
    def create_object(self, **kwargs):
        ''' You can overrride object creation in the firn save method
        ex: CustomUser.objects.register(**kwargs)
        '''
        pass

    def clean_email_confirm(self):
        ''' Check if email and confirm email are the same
        '''
        cleaned_data = super(AbstractRegistrationForm, self).clean() 
        email = cleaned_data.get('email')
        confirm = cleaned_data.get('email_confirm')
        if email != confirm:
            raise forms.ValidationError('Confirm email not matching.')
        return confirm
  
    @transaction.atomic
    def save(self):
        if self.is_valid():
            try:
                return self.create_object(
                    email=self.cleaned_data['email'],
                    password=self.cleaned_data['password'],
                    first_name=self.cleaned_data['first_name'],
                    last_name=self.cleaned_data['last_name']),
            except ValueError as e:
                self.custom_errors.append(str(e))
            except Exception as e:
                #TODO log
                print e
                self.custom_errors.append("Failed to register user.")
            return


class UserAdminBase(admin.ModelAdmin):
    list_display = ('name', 'email', 'created',)
    search_fields = ('name', 'email', )
    # list_filter = ('status', )
    exclude = ('user', )
    readonly_fields = ('created', 'modified', )
    
