from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm, Form
from .models import User, Supplier, Manufacturer
from django import forms



class AddUserForm(UserCreationForm):
	class Meta(UserCreationForm.Meta):
		model = User
		fields = UserCreationForm.Meta.fields + ('first_name','last_name','email','phone_number','address','roles')


class UpdateUserForm(ModelForm):
	class Meta:
		model = User
		fields = ['first_name','last_name','email','phone_number','address','roles']