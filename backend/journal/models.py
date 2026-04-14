# =========================================================
# Journal Models
# =========================================================

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from common.models import BaseModel
from master.models import BumonMaster, HojoKamokuMaster, KanjoKamokuMaster, ZeiMaster

User = get_user_model()


# =========================================================
# Voucher Number Generator
# =========================================================


def generate_denpyo_no(denpyo_type="SHIWAKE"):
    """Auto-generate voucher number with type prefix.

    Shiwake  → S-YYYYMMDD-NNNN
    Furikae  → F-YYYYMMDD-NNNN
    """
    prefix_char = "F" if denpyo_type == "FURIKAE" else "S"
    today = timezone.localdate()
    date_str = today.strftime("%Y%m%d")
    prefix = f"{prefix_char}-{date_str}"
    last = (
        ShiwakeDenpyo.objects.filter(denpyo_no__startswith=prefix, denpyo_type=denpyo_type).order_by("denpyo_no").last()
    )
    if last:
        seq = int(last.denpyo_no[-4:]) + 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"


# =========================================================
# Voucher Header
# =========================================================


class ShiwakeDenpyo(BaseModel):
    """Journal Entry Voucher Header.

    denpyo_type=SHIWAKE → complex N:N journal entry (仕訳日記帳)
    denpyo_type=FURIKAE → simple 1:1 internal transfer (振替伝票)
    """

    DENPYO_TYPE_CHOICES = [
        ("SHIWAKE", "仕訳"),
        ("FURIKAE", "振替"),
    ]

    denpyo_no = models.CharField(max_length=25, unique=True, verbose_name="伝票番号", editable=False)
    denpyo_type = models.CharField(
        max_length=10,
        choices=DENPYO_TYPE_CHOICES,
        default="SHIWAKE",
        verbose_name="伝票種別",
    )
    date = models.DateField(verbose_name="伝票日付")
    keijo_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="計上日付",
        help_text="会計帳簿に反映する日付。空欄の場合は伝票日付と同じ扱い。",
    )
    memo = models.CharField(max_length=200, blank=True, verbose_name="摘要")
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name="作成者",
        related_name="denpyo_set",
    )
    is_locked = models.BooleanField(default=False, verbose_name="ロック済")

    class Meta:
        verbose_name = "仕訳伝票"
        verbose_name_plural = "仕訳伝票"
        ordering = ["-date", "-denpyo_no"]

    def __str__(self):
        return f"{self.denpyo_no} ({self.date})"

    def save(self, *args, **kwargs):
        if not self.denpyo_no:
            self.denpyo_no = generate_denpyo_no(self.denpyo_type)
        super().save(*args, **kwargs)

    @property
    def effective_date(self):
        """Accounting date — falls back to document date if keijo_date is not set."""
        return self.keijo_date or self.date

    def get_kari_total(self):
        """Total Debit Amount"""
        return self.meisai.filter(kari_kashi="KA").aggregate(total=models.Sum("kingaku"))["total"] or Decimal("0")

    def get_kashi_total(self):
        """Total Credit Amount"""
        return self.meisai.filter(kari_kashi="SHI").aggregate(total=models.Sum("kingaku"))["total"] or Decimal("0")

    def validate_taisha_itchi(self):
        """Balance Check: Total Debit must equal Total Credit"""
        kari = self.get_kari_total()
        kashi = self.get_kashi_total()
        if kari != kashi:
            diff = kari - kashi
            raise ValidationError(
                f"貸借が一致していません。差額: {diff:,.0f}円 (借方: {kari:,.0f} /貸方: {kashi:,.0f})"
            )

    @property
    def get_edit_url(self):
        """Returns the appropriate update URL based on voucher type."""
        if self.denpyo_type == "FURIKAE":
            return reverse("journal:furikae-update", args=[self.pk])
        # Default to Shiwake Nikki
        return reverse("journal:shiwake-update", args=[self.pk])


# =========================================================
# Voucher Line Item
# =========================================================


class ShiwakeMeisai(BaseModel):
    """Journal Entry Line Item (Detail row)."""

    KARI_KASHI_CHOICES = [
        ("KA", "借方"),
        ("SHI", "貸方"),
    ]

    denpyo = models.ForeignKey(
        ShiwakeDenpyo,
        on_delete=models.CASCADE,
        related_name="meisai",
        verbose_name="伝票",
    )
    row_no = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="行番号",
        help_text="User-defined ordering within the voucher.",
    )
    kari_kashi = models.CharField(max_length=3, choices=KARI_KASHI_CHOICES, verbose_name="借/貸")
    kamoku = models.ForeignKey(
        KanjoKamokuMaster,
        on_delete=models.PROTECT,
        verbose_name="勘定科目",
        limit_choices_to={"level": 4, "is_active": True},
    )
    hojo = models.ForeignKey(
        HojoKamokuMaster,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="補助科目",
        limit_choices_to={"is_active": True},
    )
    bumon = models.ForeignKey(
        BumonMaster,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="部門",
        limit_choices_to={"is_active": True},
    )
    torihikisaki = models.ForeignKey(
        "master.TorihikiSakiMaster",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="取引先",
        limit_choices_to={"is_active": True},
    )
    kingaku = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="金額")
    zei_kubun = models.ForeignKey(
        ZeiMaster,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="税区分",
        limit_choices_to={"is_active": True},
    )
    tekyou = models.CharField(max_length=200, blank=True, verbose_name="摘要")

    class Meta:
        verbose_name = "仕訳明細"
        verbose_name_plural = "仕訳明細"
        ordering = ["row_no", "kari_kashi", "id"]

    def __str__(self):
        hojo_str = f" [{self.hojo}]" if self.hojo else ""
        return f"{self.get_kari_kashi_display()} {self.kamoku}{hojo_str} ¥{self.kingaku:,.0f}"

    @property
    def zei_kingaku(self):
        """Calculated tax amount (tax-inclusive reverse calculation)."""
        if not self.zei_kubun or not self.zei_kubun.tax_rate:
            return Decimal("0")
        rate = self.zei_kubun.tax_rate / 100
        return (self.kingaku * rate / (1 + rate)).quantize(Decimal("1"))

    @property
    def kingaku_nuki(self):
        """Amount excluding tax."""
        return self.kingaku - self.zei_kingaku
