# =========================================================
# Journal Forms
# =========================================================

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from master.models import BumonMaster, HojoKamokuMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster
from .models import ShiwakeDenpyo, ShiwakeMeisai
from common.forms_widgets import INPUT_CLASS, SELECT_CLASS


# =========================================================
# Shiwake Nikki — Complex N:N Journal Entry Forms
# =========================================================


class ShiwakeNikkiHeaderForm(forms.ModelForm):
    """Header form for complex journal entries (仕訳日記帳).

    Captures document date, accounting date, and overall memo.
    denpyo_type is fixed to SHIWAKE for this form.
    """

    class Meta:
        model = ShiwakeDenpyo
        fields = ["date", "keijo_date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "keijo_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "memo": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "摘要・備考（全体）"}),
        }


class ShiwakeMeisaiForm(forms.ModelForm):
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
    form=ShiwakeMeisaiForm,
    formset=BaseMeisaiFormSet,
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# =========================================================
# Furikae Denpyo — Simple 1:1 Internal Transfer Form
# =========================================================


class FurikaeHeaderForm(forms.ModelForm):
    """Header form for simple internal transfer entries (振替伝票).

    Captures document date, accounting date, and memo.
    denpyo_type is fixed to FURIKAE when saving.
    """

    class Meta:
        model = ShiwakeDenpyo
        fields = ["date", "keijo_date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "keijo_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "memo": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "摘要（任意）"}),
        }


class FurikaeRowForm(forms.Form):
    """A customized Transfer entry supporting Withdrawal, Deposit, and optional Fee.

    One submitted FurikaeRowForm creates at least two ShiwakeMeisai records,
    and a third one if a fee is applied.
    """

    # --- Withdrawal (出金側 - Credit/貸方) ---
    shukkin_kamoku = forms.ModelChoiceField(
        queryset=KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code"),
        label="出金科目",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    shukkin_hojo = forms.ModelChoiceField(
        queryset=HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code"),
        required=False,
        label="出金補助",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    shukkin_kingaku = forms.DecimalField(
        label="出金額",
        min_value=1,
        max_digits=15,
        decimal_places=0,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS + " text-right font-bold text-lg text-info",
                "step": "1",
                "placeholder": "0",
                "x-model": "shukkinKingaku",
                "x-on:input": "calcNyukin()",
            }
        ),
    )

    # --- Deposit (入金側 - Debit/借方) ---
    nyukin_kamoku = forms.ModelChoiceField(
        queryset=KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code"),
        label="入金科目",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    nyukin_hojo = forms.ModelChoiceField(
        queryset=HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code"),
        required=False,
        label="入金補助",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    nyukin_kingaku = forms.DecimalField(
        label="入金額",
        min_value=1,
        max_digits=15,
        decimal_places=0,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS + " text-right font-bold text-lg text-warning",
                "step": "1",
                "placeholder": "0",
                "x-model": "nyukinKingaku",
                "x-on:input": "calcNyukin()",
            }
        ),
    )

    # --- Fee (手数料 - Debit/借方) ---
    tesuryo_kamoku = forms.ModelChoiceField(
        queryset=KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code"),
        required=False,
        label="手数料科目",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
        # Prefill typical fee account if possible (usually 支払手数料 - code 6000 or similar)
    )
    tesuryo_zei = forms.ModelChoiceField(
        queryset=ZeiMaster.objects.filter(is_active=True).order_by("order_no"),
        required=False,
        label="対象税区分",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    tesuryo_kingaku = forms.DecimalField(
        label="手数料額",
        required=False,
        min_value=0,
        max_digits=15,
        decimal_places=0,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS + " text-right text-error font-semibold",
                "step": "1",
                "placeholder": "0",
                "x-model": "tesuryoKingaku",
                "x-on:input": "calcNyukin()",
            }
        ),
    )

    # --- Shared fields ---
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
        s_k = cleaned.get("shukkin_kingaku") or 0
        n_k = cleaned.get("nyukin_kingaku") or 0
        t_k = cleaned.get("tesuryo_kingaku") or 0

        # Validate Balance: Shukkin = Nyukin + Tesuryo
        if s_k != (n_k + t_k):
            raise forms.ValidationError(
                f"金額が一致していません。出金額(¥{s_k:,.0f}) ≠ 入金額(¥{n_k:,.0f}) + 手数料(¥{t_k:,.0f})"
            )

        if cleaned.get("shukkin_kamoku") == cleaned.get("nyukin_kamoku"):
            self.add_error("nyukin_kamoku", "出金科目と入金科目には別の勘定科目を選択してください。")

        # Validate Fee if amount exists
        if t_k > 0:
            if not cleaned.get("tesuryo_kamoku"):
                self.add_error("tesuryo_kamoku", "手数料の金額が入力されていますが、科目が選択されていません。")

        return cleaned
