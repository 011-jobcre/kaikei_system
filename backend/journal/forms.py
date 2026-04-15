# =========================================================
# Journal Forms
# =========================================================

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from master.models import BumonMaster, HojoKamokuMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster
from .models import ShiwakeDenpyo, ShiwakeMeisai
from common.forms_widgets import INPUT_CLASS, SELECT_CLASS


# =========================================================
# Furikae Denpyo — Complex N:N Internal Transfer Form
# =========================================================


class FurikaeHeaderForm(forms.ModelForm):
    """Header form for simple internal transfer entries (振替伝票).

    Captures document date, accounting date, and memo.
    denpyo_type is fixed to FURIKAE when saving.
    """

    class Meta:
        model = ShiwakeDenpyo
        fields = ["date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "memo": forms.TextInput(attrs={"placeholder": "摘要（全体）"}),
        }


class FurikaeMeisaiForm(forms.ModelForm):
    """Form for a single Journal Entry Line Item.

    Used within an inline formset for Shiwake Nikki.
    Supports both Debit (KA) and Credit (SHI) sides with sub-account (Hojo).
    """

    class Meta:
        model = ShiwakeMeisai
        fields = ["kari_kashi", "kamoku", "hojo", "bumon", "torihikisaki", "kingaku", "zei_kubun", "tekyou"]
        widgets = {
            "kari_kashi": forms.Select(
                # Alpine.js trigger to update live balance
                attrs={"class": SELECT_CLASS, "x-on:change": "calcBalance()"}
            ),
            "kamoku": forms.Select(attrs={"class": SELECT_CLASS}),
            "hojo": forms.Select(attrs={"class": SELECT_CLASS}),
            "bumon": forms.Select(attrs={"class": SELECT_CLASS}),
            "torihikisaki": forms.Select(attrs={"class": SELECT_CLASS}),
            "kingaku": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS + " text-right",
                    "step": "1",
                    "min": "0",
                    "placeholder": "0",
                    "x-on:change": "calcBalance()",
                    "x-on:keyup": "calcBalance()",
                }
            ),
            "zei_kubun": forms.Select(attrs={"class": SELECT_CLASS}),
            "tekyou": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "摘要"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only detail-level (Level 4) active accounts selectable
        self.fields["kamoku"].queryset = KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")
        self.fields["kamoku"].empty_label = "勘定科目（必須）"
        self.fields["kamoku"].required = True

        # Sub-accounts: initially shows all; filtered by JS after kamoku selection
        self.fields["hojo"].queryset = HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code")
        self.fields["hojo"].empty_label = "補助科目（任意）"

        self.fields["bumon"].queryset = BumonMaster.objects.filter(is_active=True).order_by("code")
        self.fields["bumon"].empty_label = "部門（任意）"

        self.fields["torihikisaki"].queryset = TorihikiSakiMaster.objects.filter(is_active=True).order_by("code")
        self.fields["torihikisaki"].empty_label = "取引先（任意）"

        self.fields["zei_kubun"].queryset = ZeiMaster.objects.filter(is_active=True).order_by("order_no")
        self.fields["zei_kubun"].empty_label = "税区分（任意）"


class BaseMeisaiFormSet(BaseInlineFormSet):
    """Custom FormSet validation for Shiwake Nikki.

    Ensures total debits equal total credits before save.
    """

    def clean(self):
        """Verify debit/credit balance and that at least one row exists."""
        if any(self.errors):
            return

        kari_total = 0
        kashi_total = 0
        has_row = False

        for form in self.forms:
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


# Inline formset: Header ↔ Line Items for Shiwake Nikki
MeisaiFormSet = inlineformset_factory(
    ShiwakeDenpyo,
    ShiwakeMeisai,
    form=FurikaeMeisaiForm,
    formset=BaseMeisaiFormSet,
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# =========================================================
# Shiwake Nikki — Simple 1:1 Journal Entry Forms
# =========================================================


class ShiwakeNikkiHeaderForm(forms.ModelForm):
    """Header form for complex journal entries (仕訳日記帳).

    Captures document date, accounting date, and overall memo.
    denpyo_type is fixed to SHIWAKE for this form.
    """

    pass


class FurikaeRowForm(forms.Form):
    """A customized Transfer entry supporting Withdrawal, Deposit, and optional Fee.

    One submitted FurikaeRowForm creates at least two ShiwakeMeisai records,
    and a third one if a fee is applied.
    """

    pass


class ShiwakeGridRowForm(forms.Form):
    """
    A single 1:1 row in the Spreadsheet Grid (仕訳日記帳).
    Maps to two ShiwakeMeisai records under one ShiwakeDenpyo.
    """

    date = forms.DateField(label="日付", widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}))

    # --- Debit Side (借方) ---
    kari_kamoku = forms.ModelChoiceField(
        queryset=KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code"),
        label="借方科目",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    kari_hojo = forms.ModelChoiceField(
        queryset=HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code"),
        required=False,
        label="借方補助",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    kari_zei = forms.ModelChoiceField(
        queryset=ZeiMaster.objects.filter(is_active=True).order_by("order_no"),
        required=False,
        label="借方税区分",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    # --- Amounts (金額) ---
    kari_kingaku = forms.DecimalField(
        label="借方金額",
        min_value=0,
        max_digits=15,
        decimal_places=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS + " text-right", "placeholder": "0"}),
    )
    kashi_kingaku = forms.DecimalField(
        label="貸方金額",
        min_value=0,
        max_digits=15,
        decimal_places=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS + " text-right", "placeholder": "0"}),
    )

    # --- Credit Side (貸方) ---
    kashi_kamoku = forms.ModelChoiceField(
        queryset=KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code"),
        label="貸方科目",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    kashi_hojo = forms.ModelChoiceField(
        queryset=HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code"),
        required=False,
        label="貸方補助",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    kashi_zei = forms.ModelChoiceField(
        queryset=ZeiMaster.objects.filter(is_active=True).order_by("order_no"),
        required=False,
        label="貸方税区分",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    # --- Memo (摘要) ---
    tekiyou = forms.CharField(
        label="摘要",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "摘要(明細)"}),
    )

    # --- Metadata (optional for grid) ---
    bumon = forms.ModelChoiceField(
        queryset=BumonMaster.objects.filter(is_active=True).order_by("code"),
        required=False,
        label="部門",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    torihikisaki = forms.ModelChoiceField(
        queryset=TorihikiSakiMaster.objects.filter(is_active=True).order_by("code"),
        required=False,
        label="取引先",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    def clean(self):
        cleaned = super().clean()
        kari_kingaku = cleaned.get("kari_kingaku")
        kashi_kingaku = cleaned.get("kashi_kingaku")

        if kari_kingaku is None or kashi_kingaku is None:
            raise forms.ValidationError("借方金額と貸方金額の両方を入力してください。")
        if kari_kingaku <= 0 or kashi_kingaku <= 0:
            raise forms.ValidationError("金額は0より大きい値を入力してください。")
        if kari_kingaku != kashi_kingaku:
            raise forms.ValidationError("借方金額と貸方金額が一致していません。")

        if not cleaned.get("kari_kamoku") or not cleaned.get("kashi_kamoku"):
            raise forms.ValidationError("借方科目と貸方科目は必須です。")

        if cleaned.get("kari_kamoku") == cleaned.get("kashi_kamoku") and cleaned.get("kari_hojo") == cleaned.get(
            "kashi_hojo"
        ):
            # Note: technically allowed in some accounting, but usually a mistake for 1:1 bank transfers etc.
            # We'll keep it allowed but maybe add a warning later.
            pass
        return cleaned
