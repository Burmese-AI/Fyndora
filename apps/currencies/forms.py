from django import forms
from django.utils import timezone
from iso4217 import Currency as ISO4217Currency
from decimal import Decimal

class BaseExchangeRateCreateForm(forms.ModelForm):
    
    currency_code = forms.CharField(
        label="Currency Code",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            "placeholder": "Enter currency code (e.g., USD)",
        })
    )

    effective_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            },
            format="%Y-%m-%d"
        ),
        initial=timezone.now().date,
    )

    class Meta:
        abstract = True  # This makes it a base class, not tied to any model
        fields = ["currency_code", "rate", "effective_date", "note"]
        widgets = {
            "rate": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter exchange rate",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "note": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Optional note...",
                }
            ),
        }
    
    def clean_currency_code(self):
        code = self.cleaned_data["currency_code"].upper()
        try:
            ISO4217Currency(code)
        except Exception:
            raise forms.ValidationError(f"Invalid currency code: {code}. Must be a valid ISO 4217 code (e.g., USD, EUR).")
        return code
    
    def clean_rate(self):
        rate = self.cleaned_data.get("rate")
        if rate is not None and rate <= Decimal("0"):
            raise forms.ValidationError("Rate must be greater than 0.")
        return rate
    
    def clean_note(self):
        note = self.cleaned_data.get("note")
        if note and len(note) > 255:
            raise forms.ValidationError("Note cannot exceed 255 characters.")
        return note
    
class BaseExchangeRateUpdateForm(forms.ModelForm):
    class Meta:
        abstract = True
        fields = ["note"]
        widgets = {
            "note": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Optional note...",
                }
            ),
        }
