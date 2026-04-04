from django import forms

from .models import BumonMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster
from common.forms_widgets import (
    INPUT_CLASS,
    SELECT_CLASS,
    TEXTAREA_CLASS,
    CHECKBOX_CLASS,
)


class KanjoKamokuForm(forms.ModelForm):
    """
    Form for creating / editing a Chart-of-Accounts entry (勘定科目).

    'level' and 'taisha_kubun' are intentionally excluded — they are computed
    automatically in KanjoKamokuMaster.save() from the parent account hierarchy.
    """

    class Meta:
        model = KanjoKamokuMaster
        fields = [
            "code",
            "name",
            "parent",
            "is_active",
        ]
        help_texts = {
            "parent": "親科目を選択してください。子科目は親科目の下に表示されます。",
        }
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "例: 1110",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "例: 現金",
                }
            ),
            "parent": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict parent choices to levels 1–3 so leaf accounts (level 4)
        # cannot become parents, which would break the 4-level hierarchy.
        self.fields["parent"].queryset = KanjoKamokuMaster.objects.filter(
            level__lt=4
        ).order_by("code")
        self.fields["parent"].empty_label = "指定なし"


class BumonForm(forms.ModelForm):
    """Form for creating / editing a department (部門) record."""

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
    """Form for creating / editing a tax rate entry (消費税率 マスタ)."""

    class Meta:
        model = ZeiMaster
        fields = [
            "zei_name",
            "tax_rate",
            "valid_from",
            "valid_to",
            "order_no",
            "is_active",
        ]
        widgets = {
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
    """Form for creating / editing a business partner — customer or supplier (取引先)."""

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
