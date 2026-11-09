from django import forms

TRAINING_CITIES = ("Durban", "Johannesburg", "Cape Town")


class AddTrainingForm(forms.Form):
    training = forms.ChoiceField(choices=[
        ("course", "Group course - R500 non-refundable registration"),
        ("individual", "One-on-one training"),
    ])
    city = forms.ChoiceField(
        choices=[
            ("", "Select a city"),
            *((city, city) for city in TRAINING_CITIES),
        ],
        help_text="Training is available in Durban, Johannesburg and Cape Town.",
    )
    hours = forms.IntegerField(min_value=1, max_value=10000, initial=1, required=False, help_text="For one-on-one training only (up to 10,000 hours per item).")

    def clean(self):
        data = super().clean()
        if data.get("training") == "individual" and data.get("hours") is None:
            self.add_error("hours", "Enter the number of hours for one-on-one training.")
        if data.get("training") == "course":
            data["hours"] = 1
        return data
