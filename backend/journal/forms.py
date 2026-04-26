# =========================================================
# Journal Forms
# =========================================================

from django import forms
from django.urls import reverse_lazy

from master.models import KanjoKamokuMaster, HojoKamokuMaster, BumonMaster, TorihikiSakiMaster, ZeiMaster
from .models import ShiwakeDenpyo, ShiwakeMeisai
from django.forms import BaseInlineFormSet, inlineformset_factory
from common.forms_widgets import INPUT_CLASS, SELECT_CLASS

EMPTY_CHOICE_LABEL = "---------"
SEARCH_META_SEPARATOR = "|||"


# =========================================================
# Common Queryset Helpers
# =========================================================


def get_active_level4_kamoku_queryset():
    """Return active Level-4 (detail) kamoku accounts ordered by code."""
    return KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")


def get_active_hojo_queryset():
    """Return active sub-accounts ordered by kamoku code and code."""
    return HojoKamokuMaster.objects.filter(is_active=True).order_by("kamoku__code", "code")


def get_active_bumon_queryset():
    """Return active departments ordered by code."""
    return BumonMaster.objects.filter(is_active=True).order_by("code")


def get_active_torihiki_queryset():
    """Return active business partners ordered by code."""
    return TorihikiSakiMaster.objects.filter(is_active=True).order_by("code")


def get_active_zei_queryset():
    """Return active tax rates ordered by order_no."""
    return ZeiMaster.objects.filter(is_active=True).order_by("order_no")


def build_searchable_label(display_text, *search_parts):
    search_text = " ".join(str(part).strip() for part in search_parts if str(part).strip())
    return f"{display_text} {SEARCH_META_SEPARATOR} {search_text}" if search_text else display_text


class KanjoKamokuChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return build_searchable_label(obj.name, obj.code, obj.name, obj.furigana or "")


class HojoKamokuChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return build_searchable_label(obj.name, obj.code, obj.name, obj.furigana or "")


class BumonChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return build_searchable_label(obj.name, obj.code, obj.name)


class TorihikiSakiChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return build_searchable_label(obj.name, obj.code, obj.name)


def setup_master_fields(form):
    """Configure common master data field querysets and empty labels."""
    form.fields["kamoku"] = KanjoKamokuChoiceField(
        queryset=get_active_level4_kamoku_queryset(),
        empty_label=EMPTY_CHOICE_LABEL,
        required=True,
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "hx-get": reverse_lazy("journal:load-hojo"),
                "hx-target": f"#id_{form.add_prefix('hojo')}",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        ),
    )
    # Filter hojo queryset if kamoku is selected
    kamoku_id = None
    if form.is_bound:
        kamoku_id = form.data.get(form.add_prefix("kamoku"))
    elif form.instance and form.instance.pk:
        kamoku_id = form.instance.kamoku_id

    hojo_qs = get_active_hojo_queryset()
    if kamoku_id:
        try:
            hojo_qs = hojo_qs.filter(kamoku_id=kamoku_id)
        except (ValueError, TypeError):
            pass

    form.fields["hojo"] = HojoKamokuChoiceField(
        queryset=hojo_qs,
        empty_label=EMPTY_CHOICE_LABEL,
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    form.fields["bumon"] = BumonChoiceField(
        queryset=get_active_bumon_queryset(),
        empty_label=EMPTY_CHOICE_LABEL,
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    form.fields["torihikisaki"] = TorihikiSakiChoiceField(
        queryset=get_active_torihiki_queryset(),
        empty_label=EMPTY_CHOICE_LABEL,
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    form.fields["zei_kubun"].queryset = get_active_zei_queryset()
    form.fields["zei_kubun"].empty_label = EMPTY_CHOICE_LABEL


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
        setup_master_fields(self)

        if self.errors:
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    existing_classes = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = f"{existing_classes} border-error text-error".strip()

    def clean_kingaku(self):
        kingaku = self.cleaned_data.get("kingaku")
        if kingaku is not None and kingaku < 0:
            raise forms.ValidationError("金額にマイナス値は入力できません。")
        return kingaku


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


class ShiwakeMeisaiForm(forms.Form):
    """
    A single 1:1 row in the Spreadsheet Grid (仕訳日記帳).
    Maps to two ShiwakeMeisai records under one ShiwakeDenpyo.
    """

    denpyo_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    date = forms.DateField(label="日付", widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}))

    # --- Debit Side (借方) ---
    kari_kamoku = KanjoKamokuChoiceField(
        queryset=get_active_level4_kamoku_queryset(),
        label="借方科目",
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "data-placeholder": "科目を検索...",
                "hx-get": reverse_lazy("journal:load-hojo"),
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        ),
    )
    kari_hojo = HojoKamokuChoiceField(
        queryset=get_active_hojo_queryset(),
        required=False,
        label="借方補助",
        widget=forms.Select(attrs={"class": SELECT_CLASS, "data-placeholder": "補助科目を検索..."}),
    )
    kari_zei = forms.ModelChoiceField(
        queryset=get_active_zei_queryset(),
        required=False,
        label="借方税区分",
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "data-placeholder": "税区分を検索...",
                "data-no-parse": "true",
            }
        ),
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
    kashi_kamoku = KanjoKamokuChoiceField(
        queryset=get_active_level4_kamoku_queryset(),
        label="貸方科目",
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "data-placeholder": "科目を検索...",
                "hx-get": reverse_lazy("journal:load-hojo"),
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        ),
    )
    kashi_hojo = HojoKamokuChoiceField(
        queryset=get_active_hojo_queryset(),
        required=False,
        label="貸方補助",
        widget=forms.Select(attrs={"class": SELECT_CLASS, "data-placeholder": "補助科目を検索..."}),
    )
    kashi_zei = forms.ModelChoiceField(
        queryset=get_active_zei_queryset(),
        required=False,
        label="貸方税区分",
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "data-placeholder": "税区分を検索...",
                "data-no-parse": "true",
            }
        ),
    )

    # --- Memo (摘要) ---
    tekiyou = forms.CharField(
        label="摘要",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "摘要(明細)"}),
    )

    # --- Metadata (optional for grid) ---
    bumon = BumonChoiceField(
        queryset=get_active_bumon_queryset(),
        required=False,
        label="部門",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    torihikisaki = TorihikiSakiChoiceField(
        queryset=get_active_torihiki_queryset(),
        required=False,
        label="取引先",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        row_idx = (self.prefix or "row-0").replace("row-", "")
        field_positions = {
            "kari_kamoku": 1,
            "kari_hojo": 2,
            "kari_zei": 4,
            "kashi_kamoku": 5,
            "kashi_hojo": 6,
            "kashi_zei": 8,
        }
        for field_name, col_idx in field_positions.items():
            self.fields[field_name].widget.attrs.update({"data-row": row_idx, "data-col": str(col_idx)})

        # Set specific HTMX targets for dependent dropdowns
        self.fields["kari_kamoku"].widget.attrs["hx-target"] = f"#id_{self.add_prefix('kari_hojo')}"
        self.fields["kashi_kamoku"].widget.attrs["hx-target"] = f"#id_{self.add_prefix('kashi_hojo')}"

        # Filter hojo querysets if kamoku is selected
        for side in ["kari", "kashi"]:
            kamoku_field = f"{side}_kamoku"
            hojo_field = f"{side}_hojo"
            kamoku_id = None
            if self.is_bound:
                kamoku_id = self.data.get(self.add_prefix(kamoku_field))
            else:
                kamoku_id = self.initial.get(kamoku_field)
                if hasattr(kamoku_id, "id"):
                    kamoku_id = kamoku_id.id

            if kamoku_id:
                try:
                    self.fields[hojo_field].queryset = get_active_hojo_queryset().filter(kamoku_id=kamoku_id)
                except (ValueError, TypeError):
                    pass

        if self.errors:
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    existing_classes = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = f"{existing_classes} border-error text-error".strip()

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
