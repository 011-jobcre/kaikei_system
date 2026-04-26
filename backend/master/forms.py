# =========================================================
# Master Forms
# =========================================================

from django import forms
from .models import KanjoKamokuMaster, HojoKamokuMaster, BumonMaster, ZeiMaster, TorihikiSakiMaster, ShiwakeDictionary
from common.forms_widgets import INPUT_CLASS, SELECT_CLASS, TEXTAREA_CLASS, CHECKBOX_CLASS

EMPTY_CHOICE_LABEL = "---------"
SEARCH_META_SEPARATOR = "|||"


def build_searchable_label(display_text, *search_parts):
    search_text = " ".join(str(part).strip() for part in search_parts if str(part).strip())
    return f"{display_text} {SEARCH_META_SEPARATOR} {search_text}" if search_text else display_text


class BaseMasterForm(forms.ModelForm):
    """Base form with common validation for master data."""

    class Meta:
        error_messages = {"code": {"unique": "このコードは既に存在しています。別のコードを入力してください。"}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.errors:
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    # Add error styling to fields with validation errors
                    existing_classes = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = f"{existing_classes} border-error text-error".strip()

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

    class Meta(BaseMasterForm.Meta):
        model = KanjoKamokuMaster
        fields = ["code", "name", "furigana", "parent", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 111010"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 現金"}),
            "furigana": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: genkin"}),
            "parent": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        help_texts = {"parent": "親科目を選択してください。子科目は親科目の下に表示されます。"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict parent choices to levels 1–3 so leaf accounts (level 4)
        # cannot become parents, which would break the 4-level hierarchy.
        self.fields["parent"].queryset = KanjoKamokuMaster.objects.filter(level__lt=4).order_by("code")
        self.fields["parent"].label_from_instance = lambda obj: build_searchable_label(
            f"{obj.level} {'-'} {'　' * max((obj.level or 1) - 1, 0)}{obj.get_taisha_kubun_display() or '-'} {'-'} {obj.name}",
            obj.code,
            obj.name,
            obj.furigana or "",
        )
        self.fields["parent"].empty_label = EMPTY_CHOICE_LABEL


class HojoKamokuForm(forms.ModelForm):
    """Form for creating / editing a Sub-account (補助科目) record.

    Sub-accounts are tied to a single Level-4 main account (kamoku).
    The code must be unique within the same parent account.
    """

    class Meta:
        model = HojoKamokuMaster
        fields = ["code", "name", "furigana", "kamoku", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: H100"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: みずほ銀行"}),
            "furigana": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: mizuho ginkou"}),
            "kamoku": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {"__all__": {"unique_together": "この科目コードの組み合わせは既に存在しています。"}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only Level-4 (detail/leaf) active accounts can have sub-accounts
        self.fields["kamoku"].queryset = KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")
        self.fields["kamoku"].label_from_instance = lambda obj: build_searchable_label(
            obj.name, obj.code, obj.name, obj.furigana or ""
        )
        self.fields["kamoku"].empty_label = EMPTY_CHOICE_LABEL


class BumonForm(BaseMasterForm):
    """Form for creating / editing a department (部門) record."""

    class Meta(BaseMasterForm.Meta):
        model = BumonMaster
        fields = ["code", "name", "manager_name", "annual_budget", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: D001"}),
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 営業部"}),
            "manager_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "annual_budget": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }


class ZeiForm(forms.ModelForm):
    """Form for creating / editing a tax rate entry (税) record."""

    class Meta:
        model = ZeiMaster
        fields = ["zei_name", "tax_rate", "valid_from", "valid_to", "order_no", "is_active"]
        widgets = {
            "zei_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "tax_rate": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "1", "min": "0", "max": "100"}),
            "valid_from": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "valid_to": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "order_no": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }
        error_messages = {
            "valid_from": {"min_value": "適用開始日は1900/01/01以降の日付を入力してください。"},
            "valid_to": {"max_value": "適用終了日は2100/12/31以前の日付を入力してください。"},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure tax_rate is displayed as an integer in the form input
        if self.instance and self.instance.pk:
            self.initial["tax_rate"] = int(self.instance.tax_rate)
        elif "tax_rate" in self.initial and self.initial["tax_rate"] is not None:
            self.initial["tax_rate"] = int(self.initial["tax_rate"])

    def clean_valid_to(self):
        valid_from = self.cleaned_data.get("valid_from")
        valid_to = self.cleaned_data.get("valid_to")
        if valid_from and valid_to and valid_to < valid_from:
            raise forms.ValidationError("適用終了日は適用開始日以降の日付を入力してください。")
        return valid_to

    def clean_tax_rate(self):
        tax_rate = self.cleaned_data.get("tax_rate")
        if tax_rate > 100 or tax_rate < 0:
            raise forms.ValidationError("税率は100%以下、0%以上で入力してください。")
        return tax_rate


class TorihikiSakiForm(BaseMasterForm):
    """Form for creating / editing a business partner — customer or supplier (取引先) record."""

    class Meta(BaseMasterForm.Meta):
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

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and not phone.replace("-", "").isdigit():
            raise forms.ValidationError("電話番号は数字とハイフンのみで入力してください。")
        return phone


class ShiwakeDictionaryForm(forms.ModelForm):
    """Form for creating / editing a Journal Dictionary pattern (仕訳辞書)."""

    class Meta:
        model = ShiwakeDictionary
        fields = [
            "name",
            "shortcut_code",
            "kari_kamoku",
            "kari_hojo",
            "kari_zei",
            "kashi_kamoku",
            "kashi_hojo",
            "kashi_zei",
            "tekiyou",
            "bumon",
            "torihikisaki",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: 水道光熱費支払"}),
            "shortcut_code": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "例: D100"}),
            "kari_kamoku": forms.Select(attrs={"class": SELECT_CLASS}),
            "kari_hojo": forms.Select(attrs={"class": SELECT_CLASS}),
            "kari_zei": forms.Select(attrs={"class": SELECT_CLASS}),
            "kashi_kamoku": forms.Select(attrs={"class": SELECT_CLASS}),
            "kashi_hojo": forms.Select(attrs={"class": SELECT_CLASS}),
            "kashi_zei": forms.Select(attrs={"class": SELECT_CLASS}),
            "tekiyou": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "bumon": forms.Select(attrs={"class": SELECT_CLASS}),
            "torihikisaki": forms.Select(attrs={"class": SELECT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        account_label_fn = lambda obj: build_searchable_label(obj.name, obj.code, obj.name, obj.furigana or "")

        # Apply constraints and formatting to choice fields
        active_kamoku = KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")
        active_hojo = HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code")
        active_zei = ZeiMaster.objects.filter(is_active=True).order_by("order_no")
        active_bumon = BumonMaster.objects.filter(is_active=True).order_by("code")
        active_torihiki = TorihikiSakiMaster.objects.filter(is_active=True).order_by("code")

        # Kari side
        self.fields["kari_kamoku"].queryset = active_kamoku
        self.fields["kari_kamoku"].label_from_instance = account_label_fn
        self.fields["kari_kamoku"].empty_label = EMPTY_CHOICE_LABEL
        self.fields["kari_hojo"].queryset = active_hojo
        self.fields["kari_hojo"].label_from_instance = account_label_fn
        self.fields["kari_hojo"].empty_label = EMPTY_CHOICE_LABEL
        self.fields["kari_zei"].queryset = active_zei
        self.fields["kari_zei"].empty_label = EMPTY_CHOICE_LABEL

        # Kashi side
        self.fields["kashi_kamoku"].queryset = active_kamoku
        self.fields["kashi_kamoku"].label_from_instance = account_label_fn
        self.fields["kashi_kamoku"].empty_label = EMPTY_CHOICE_LABEL
        self.fields["kashi_hojo"].queryset = active_hojo
        self.fields["kashi_hojo"].label_from_instance = account_label_fn
        self.fields["kashi_hojo"].empty_label = EMPTY_CHOICE_LABEL
        self.fields["kashi_zei"].queryset = active_zei
        self.fields["kashi_zei"].empty_label = EMPTY_CHOICE_LABEL

        # Metadata
        self.fields["bumon"].queryset = active_bumon
        self.fields["bumon"].empty_label = EMPTY_CHOICE_LABEL
        self.fields["torihikisaki"].queryset = active_torihiki
        self.fields["torihikisaki"].empty_label = EMPTY_CHOICE_LABEL
