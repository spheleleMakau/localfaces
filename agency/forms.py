from django import forms

TRAINING_CITIES = ("Durban", "Johannesburg", "Cape Town")


class AddTrainingForm(forms.Form):
    training = forms.ChoiceField(choices=[
        ("course", "Group course - R500 non-refundable registration"),
        ("individual", "One-on-one training - minimum 3 sessions"),
    ])
    city = forms.ChoiceField(
        choices=[
            ("", "Select a city"),
            *((city, city) for city in TRAINING_CITIES),
        ],
        help_text="Training is available in Durban, Johannesburg and Cape Town.",
    )
