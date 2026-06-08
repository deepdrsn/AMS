from django import forms


class AttendanceActionForm(forms.Form):
    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)
    accuracy = forms.FloatField(required=False)


class BreakActionForm(forms.Form):
    ACTION_CHOICES = [
        ('start', 'Start Break'),
        ('end', 'End Break'),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)
    accuracy = forms.FloatField(required=False)


