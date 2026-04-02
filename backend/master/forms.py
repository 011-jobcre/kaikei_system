from django import forms

from .models import BumonMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster

# --- 共通ウィジェットクラス ---
INPUT_CLASS = "input input-bordered input-sm w-full"
SELECT_CLASS = "select select-bordered select-sm w-full"
TEXTAREA_CLASS = "textarea textarea-bordered textarea-sm w-full"
CHECKBOX_CLASS = "checkbox checkbox-sm checkbox-primary"


class KanjoKamokuForm(forms.ModelForm):
    class Meta:
        model = KanjoKamokuMaster
        fields = [
            "code",
            "name",
            # "level",
            "parent",
            # "taisha_kubun",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "例: 1110"}
            ),
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "例: 現金"}
            ),
            # "level": forms.NumberInput(
            #     attrs={"class": INPUT_CLASS, "min": 1, "max": 4}
            # ),
            "parent": forms.Select(attrs={"class": SELECT_CLASS}),
            # "taisha_kubun": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 親科目はLevel 4未満のみ選択可
        self.fields["parent"].queryset = KanjoKamokuMaster.objects.filter(
            level__lt=4
        ).order_by("code")
        self.fields["parent"].empty_label = "指定なし"


class BumonForm(forms.ModelForm):
    class Meta:
        model = BumonMaster
        fields = [
            "code",
            "name",
            "manager_name",
            "annual_budget",
            "is_active",
            "order_no",
        ]
        widgets = {
            "code": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "例: D001"}
            ),
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "例: 営業部"}
            ),
            "manager_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "annual_budget": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "step": "0.01"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "order_no": forms.NumberInput(attrs={"class": INPUT_CLASS}),
        }


class ZeiForm(forms.ModelForm):
    class Meta:
        model = ZeiMaster
        fields = [
            "zei_kubun",
            "zei_name",
            "tax_rate",
            "valid_from",
            "valid_to",
            "order_no",
            "is_active",
        ]
        widgets = {
            "zei_kubun": forms.Select(attrs={"class": SELECT_CLASS}),
            "zei_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "tax_rate": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "step": "0.01", "min": "0", "max": "100"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
            "valid_from": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "valid_to": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "order_no": forms.NumberInput(attrs={"class": INPUT_CLASS}),
        }


class TorihikiSakiForm(forms.ModelForm):
    class Meta:
        model = TorihikiSakiMaster
        fields = ["code", "name", "address", "phone", "email", "is_active"]
        widgets = {
            "code": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "例: T001"}
            ),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "address": forms.Textarea(attrs={"class": TEXTAREA_CLASS, "rows": 3}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "type": "tel"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
