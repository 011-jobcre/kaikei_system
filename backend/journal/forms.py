from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from master.models import BumonMaster, KanjoKamokuMaster, ZeiMaster
from .models import ShiwakeDenpyo, ShiwakeMeisai
from common.forms_widgets import (
    INPUT_CLASS,
    SELECT_CLASS,
)


class ShiwakeDenpyoForm(forms.ModelForm):
    """
    Form for the Journal Entry Header (仕訳伝票).
    Captures the date and overall memo for the transaction.
    """

    class Meta:
        model = ShiwakeDenpyo
        fields = ["date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "memo": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "摘要・備考（全体）"}
            ),
        }


class ShiwakeMeisaiForm(forms.ModelForm):
    """
    Form for a single Journal Entry Line Item (仕訳明細).
    Used within an inline formset.
    """

    class Meta:
        model = ShiwakeMeisai
        fields = ["kari_kashi", "kamoku", "bumon", "kingaku", "zei_kubun", "tekyou"]
        widgets = {
            "kari_kashi": forms.Select(
                # Alpine.js event trigger to update live balance on user input
                attrs={"class": SELECT_CLASS, "x-on:change": "calcBalance()"}
            ),
            "kamoku": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),
            "bumon": forms.Select(attrs={"class": SELECT_CLASS}),
            "kingaku": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "1",
                    "min": "0",
                    "placeholder": "0",
                    # Alpine.js event trigger to update live balance on user input
                    "x-on:change": "calcBalance()",
                    "x-on:keyup": "calcBalance()",
                }
            ),
            "zei_kubun": forms.Select(attrs={"class": SELECT_CLASS}),
            "tekyou": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "摘要"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit accounts to detail-level (Level 4) and active accounts only
        self.fields["kamoku"].queryset = KanjoKamokuMaster.objects.filter(
            level=4, is_active=True
        ).order_by("code")
        self.fields["kamoku"].empty_label = "科目を選択"

        # Limit departments and tax rates to active records
        self.fields["bumon"].queryset = BumonMaster.objects.filter(
            is_active=True
        ).order_by("order_no", "code")
        self.fields["bumon"].empty_label = "部門（任意）"

        self.fields["zei_kubun"].queryset = ZeiMaster.objects.filter(
            is_active=True
        ).order_by("order_no")
        self.fields["zei_kubun"].empty_label = "税区分（任意）"


class BaseMeisaiFormSet(BaseInlineFormSet):
    """
    Custom FormSet validation logic to ensure the journal entry is mathematically valid.
    """

    def clean(self):
        """
        Verify that total debits match total credits (貸借一致),
        and that at least one valid line item exists.
        """
        if any(self.errors):
            return

        kari_total = 0
        kashi_total = 0
        has_row = False

        for form in self.forms:
            # Ignore marked-for-deletion forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE"):
                has_row = True
                kari_kashi = form.cleaned_data.get("kari_kashi")
                kingaku = form.cleaned_data.get("kingaku", 0) or 0

                if kari_kashi == "KA":
                    kari_total += kingaku
                elif kari_kashi == "SHI":
                    kashi_total += kingaku

        if not has_row:
            raise forms.ValidationError("少なくとも1行の明細を入力してください。")

        if kari_total != kashi_total:
            diff = kari_total - kashi_total
            raise forms.ValidationError(
                f"貸借が一致していません。差額: ¥{diff:,.0f}"
                f" (借方合計: ¥{kari_total:,.0f} / 貸方合計: ¥{kashi_total:,.0f})"
            )


# Inline formset factory linking the Header and Line Items together
MeisaiFormSet = inlineformset_factory(
    ShiwakeDenpyo,
    ShiwakeMeisai,
    form=ShiwakeMeisaiForm,
    formset=BaseMeisaiFormSet,
    extra=2,  # Show 2 empty rows by default
    can_delete=True,  # Allow removing rows
    min_num=1,  # Require at least 1 row (backed up by clean() method)
    validate_min=True,
)
