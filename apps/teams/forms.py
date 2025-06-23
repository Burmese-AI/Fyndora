from django import forms
from .models import Team

class TeamCreationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.org_member = kwargs.pop("org_member", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Team
        fields = ['title', 'description', 'team_coordinator', 'custom_remittance_rate']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base',
                    'placeholder': 'Enter team title',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'textarea textarea-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base min-h-[60px]',
                    'rows': 2,
                    'placeholder': 'Describe your team (optional)',
                }
            ),
            'team_coordinator': forms.Select(
                attrs={
                    'class': 'select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base',
                }
            ),
            'custom_remittance_rate': forms.NumberInput(
                attrs={
                    'class': 'input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base',
                    'placeholder': 'Enter custom remittance rate',
                }
            ),

        }


    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title.strip():
            raise forms.ValidationError("Team titles cannot be blank")
        return title
    
    def clean_coordinator(self):
        team_coordinator = self.cleaned_data.get("team_coordinator")
        if not team_coordinator or not team_coordinator.strip():
            raise forms.ValidationError("You must choose at least one Team Coordinator")
        return team_coordinator