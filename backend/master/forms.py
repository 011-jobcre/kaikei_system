from django import forms
from .models import BumonMaster, HojoKamokuMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster
from common.forms_widgets import (
    INPUT_CLASS,
    SELECT_CLASS,
    TEXTAREA_CLASS,
    CHECKBOX_CLASS,
)


class BaseMasterForm(forms.ModelForm):
    """Base form with common validation for master data."""

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        if code and len(code) > 6:
            raise forms.ValidationError({"code": "コードは半角英数字6文字で入力してください。"})
        name = cleaned_data.get("name")
        if name and len(name) > 50:
            raise forms.ValidationError({"name": "名称は50文字以内で入力してください。"})
        return cleaned_data


class KanjoKamokuForm(BaseMasterForm):
    """
    Form for creating / editing an account (勘定科目) record.

    'level' and 'taisha_kubun' are intentionally excluded — they are computed
    automatically in KanjoKamokuMaster.save() from the parent account hierarchy.
    """

    class Meta:
        model = KanjoKamokuMaster
        fields = ["code", "name", "parent", "is_active"]
        help_texts = {"parent": "親科目を選択してください。子科目は親科目の下に表示されます。"}
        widgets = {
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 111010"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 現金"}),
            "parent": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {"code": {"unique": "このコードは既に存在しています。別のコードを入力してください。"}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict parent choices to levels 1–3 so leaf accounts (level 4)
        # cannot become parents, which would break the 4-level hierarchy.
        self.fields["parent"].queryset = KanjoKamokuMaster.objects.filter(level__lt=4).order_by("code")
        self.fields["parent"].empty_label = "指定なし"


class BumonForm(BaseMasterForm):
    """Form for creating / editing a department (部門) record."""

    class Meta:
        model = BumonMaster
        fields = ["code", "name", "manager_name", "annual_budget", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: D001"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 営業部"}),
            "manager_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "annual_budget": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {"code": {"unique": "このコードは既に存在しています。別のコードを入力してください。"}}


class ZeiForm(forms.ModelForm):
    """Form for creating / editing a tax rate entry (税) record."""

    class Meta:
        model = ZeiMaster
        fields = ["zei_name", "tax_rate", "valid_from", "valid_to", "order_no", "is_active"]
        widgets = {
            "zei_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "tax_rate": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01", "min": "0", "max": "100"}),
            "valid_from": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "valid_to": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "order_no": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {
            "valid_from": {"min_value": "適用開始日は1900/01/01以降の日付を入力してください。"},
            "valid_to": {"max_value": "適用終了日は2100/12/31以前の日付を入力してください。"},
        }

    def clean_valid_to(self):
        valid_from = self.cleaned_data.get("valid_from")
        valid_to = self.cleaned_data.get("valid_to")
        if valid_from and valid_to and valid_to < valid_from:
            raise forms.ValidationError("適用終了日は適用開始日以降の日付を入力してください。")
        return valid_to


class TorihikiSakiForm(BaseMasterForm):
    """Form for creating / editing a business partner — customer or supplier (取引先) record."""

    class Meta:
        model = TorihikiSakiMaster
        fields = ["code", "name", "address", "phone", "email", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: T001"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "address": forms.Textarea(attrs={"class": TEXTAREA_CLASS, "rows": 2}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "type": "tel"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {"code": {"unique": "このコードは既に存在しています。別のコードを入力してください。"}}

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and not phone.replace("-", "").isdigit():
            raise forms.ValidationError("電話番号は数字とハイフンのみで入力してください。")
        return phone


class HojoKamokuForm(forms.ModelForm):
    """Form for creating / editing a Sub-account (補助科目) record.

    Sub-accounts are tied to a single Level-4 main account (kamoku).
    The code must be unique within the same parent account.
    """

    class Meta:
        model = HojoKamokuMaster
        fields = ["kamoku", "code", "name", "is_active"]
        widgets = {
            "kamoku": forms.Select(attrs={"class": SELECT_CLASS}),
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: H100"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: みずほ銀行"}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {"__all__": {"unique_together": "この科目コードの組み合わせは既に存在しています。"}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only Level-4 (detail/leaf) active accounts can have sub-accounts
        self.fields["kamoku"].queryset = KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")
        self.fields["kamoku"].empty_label = "勘定科目を選択"
