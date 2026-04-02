from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from master.models import BumonMaster, KanjoKamokuMaster, ZeiMaster

from .models import ShiwakeDenpyo, ShiwakeMeisai

INPUT_CLASS = "input input-bordered input-sm w-full"
SELECT_CLASS = "select select-bordered select-sm w-full"


class ShiwakeDenpyoForm(forms.ModelForm):
    class Meta:
        model = ShiwakeDenpyo
        fields = ["date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "memo": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "摘要・備考"}
            ),
        }


class ShiwakeMeisaiForm(forms.ModelForm):
    class Meta:
        model = ShiwakeMeisai
        fields = ["kari_kashi", "kamoku", "bumon", "kingaku", "zei_kubun", "tekyou"]
        widgets = {
            "kari_kashi": forms.Select(
                attrs={"class": SELECT_CLASS, "x-model": "kari_kashi"}
            ),
            "kamoku": forms.Select(
                attrs={
                    "class": f"{SELECT_CLASS} tomselect",
                    "data-placeholder": "科目コード/名称で検索",
                }
            ),
            "bumon": forms.Select(attrs={"class": SELECT_CLASS}),
            "kingaku": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "1",
                    "min": "0",
                    "placeholder": "0",
                    "x-on:change": "calcBalance()",
                }
            ),
            "zei_kubun": forms.Select(attrs={"class": SELECT_CLASS}),
            "tekyou": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "摘要"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Level4 かつ有効な科目のみ
        self.fields["kamoku"].queryset = KanjoKamokuMaster.objects.filter(
            level=4, is_active=True
        ).order_by("code")
        self.fields["kamoku"].empty_label = "── 科目を選択 ──"
        self.fields["bumon"].queryset = BumonMaster.objects.filter(
            is_active=True
        ).order_by("order_no", "code")
        self.fields["bumon"].empty_label = "── 部門（任意）──"
        self.fields["zei_kubun"].queryset = ZeiMaster.objects.filter(
            is_active=True
        ).order_by("order_no")
        self.fields["zei_kubun"].empty_label = "── 税区分（任意）──"


class BaseMeisaiFormSet(BaseInlineFormSet):
    def clean(self):
        """貸借一致チェック（FormSetレベル）"""
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
