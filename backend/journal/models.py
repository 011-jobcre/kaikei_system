# =========================================================
# Journal Models
# =========================================================

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone

from common.models import BaseModel
from master.models import KanjoKamokuMaster, HojoKamokuMaster, BumonMaster, ZeiMaster, TorihikiSakiMaster

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
# Journal Header
# =========================================================


class ShiwakeDenpyo(BaseModel):
    """Journal Entry Voucher Header.

    denpyo_type=SHIWAKE → journal book style entries (仕訳日記帳)
    denpyo_type=FURIKAE → professional voucher style entries (振替伝票)
    """

    DENPYO_TYPE_CHOICES = [
        ("SHIWAKE", "仕訳"),
        ("FURIKAE", "振替"),
    ]

    denpyo_no = models.CharField(verbose_name="伝票番号", max_length=25, unique=True, editable=False)
    denpyo_type = models.CharField(
        verbose_name="伝票種別",
        max_length=10,
        choices=DENPYO_TYPE_CHOICES,
        default="SHIWAKE",
    )
    date = models.DateField(verbose_name="伝票日付")
    memo = models.CharField(verbose_name="摘要（全体）", max_length=200, blank=True)
    created_by = models.ForeignKey(
        User,
        verbose_name="作成者",
        on_delete=models.PROTECT,
        related_name="denpyo_set",
    )
    is_locked = models.BooleanField(verbose_name="ロック済", default=False)

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
    def get_edit_url(self):
        """Return the appropriate editor URL for the voucher type."""
        if self.denpyo_type == "FURIKAE":
            return reverse("journal:furikae-update", args=[self.pk])
        return f"{reverse('journal:shiwake-create')}?edit_id={self.pk}"


# =========================================================
# Journal Line Item
# =========================================================


class ShiwakeMeisai(BaseModel):
    """Journal Entry Line Item (Detail row)."""

    KARI_KASHI_CHOICES = [
        ("KA", "借方"),
        ("SHI", "貸方"),
    ]

    denpyo = models.ForeignKey(
        ShiwakeDenpyo,
        verbose_name="伝票",
        on_delete=models.CASCADE,
        related_name="meisai",
    )
    row_no = models.PositiveSmallIntegerField(verbose_name="行番号", default=0)
    kari_kashi = models.CharField(verbose_name="借/貸", max_length=3, choices=KARI_KASHI_CHOICES)
    kamoku = models.ForeignKey(
        KanjoKamokuMaster,
        verbose_name="勘定科目",
        on_delete=models.PROTECT,
        limit_choices_to={"level": 4, "is_active": True},
    )
    hojo = models.ForeignKey(
        HojoKamokuMaster,
        verbose_name="補助科目",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={"is_active": True},
    )
    bumon = models.ForeignKey(
        BumonMaster,
        verbose_name="部門",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={"is_active": True},
    )
    torihikisaki = models.ForeignKey(
        TorihikiSakiMaster,
        verbose_name="取引先",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={"is_active": True},
    )
    zei_kubun = models.ForeignKey(
        ZeiMaster,
        verbose_name="税区分",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={"is_active": True},
    )
    kingaku = models.DecimalField(verbose_name="金額", max_digits=15, decimal_places=0)
    tekyou = models.CharField(verbose_name="摘要", max_length=200, blank=True)

    class Meta:
        verbose_name = "仕訳明細"
        verbose_name_plural = "仕訳明細"
        ordering = ["row_no", "kari_kashi", "id"]

    def __str__(self):
        hojo_str = f" [{self.hojo}]" if self.hojo else ""
        return f"{self.get_kari_kashi_display()} {self.kamoku}{hojo_str} ¥{self.kingaku:,.0f}"

    @property
    def aite_kamoku_display(self):
        """Returns the counter-account name for ledger displays.
        Standard behavior: If 1 counter-account, show name. If multiple, show '諸口'.
        """
        # Get all lines in the voucher (expects denpyo__meisai__kamoku prefetch)
        all_meisai = list(self.denpyo.meisai.all())
        opposite_side = [m for m in all_meisai if m.kari_kashi != self.kari_kashi]

        if not opposite_side:
            return "—"

        # Determine prefix based on the opposite side
        # If current is KA (Debit), opposite is SHI (Credit) -> [貸方科目]
        # If current is SHI (Credit), opposite is KA (Debit) -> [借方科目]
        prefix = "[貸方科目] " if self.kari_kashi == "KA" else "[借方科目] "

        # Unique counter account IDs
        unique_kamokus = {m.kamoku_id for m in opposite_side}

        if len(unique_kamokus) == 1 and len(opposite_side) == 1:
            m = opposite_side[0]
            name = m.kamoku.name
            if m.hojo:
                name = f"{name} / {m.hojo.name}"
            return f"{prefix}{name}"
        else:
            # If multiple items on opposite side, return Shokuchi (standard)
            # Even if they share the same main account, the presence of multiple detail rows usually triggers 諸口
            # unless we want to roll them up. Accounting standard typically uses 諸口 for multi-line.
            return f"{prefix}諸口"

    @property
    def voucher_tekyous(self):
        """Returns all unique tekyou values from the whole voucher, joined by newlines."""
        all_meisai = self.denpyo.meisai.all()
        tekyous = []
        for m in all_meisai:
            if m.tekyou and m.tekyou not in tekyous:
                tekyous.append(m.tekyou)

        if not tekyous:
            return ""
        return "\n".join(tekyous)

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
