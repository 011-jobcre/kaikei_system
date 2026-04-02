from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import BaseModel
from master.models import BumonMaster, KanjoKamokuMaster, ZeiMaster

User = get_user_model()


def generate_denpyo_no():
    """伝票番号を YYYYMMDD-NNNN 形式で自動生成"""
    today = timezone.localdate()
    prefix = today.strftime("%Y%m%d")
    last = (
        ShiwakeDenpyo.objects.filter(denpyo_no__startswith=prefix)
        .order_by("denpyo_no")
        .last()
    )
    if last:
        seq = int(last.denpyo_no[-4:]) + 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"


class ShiwakeDenpyo(BaseModel):
    """仕訳伝票ヘッダー"""

    denpyo_no = models.CharField(
        max_length=20, unique=True, verbose_name="伝票番号", editable=False
    )
    date = models.DateField(verbose_name="日付")
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
            self.denpyo_no = generate_denpyo_no()
        super().save(*args, **kwargs)

    def get_kari_total(self):
        """借方合計金額"""
        return self.meisai.filter(kari_kashi="KA").aggregate(
            total=models.Sum("kingaku")
        )["total"] or Decimal("0")

    def get_kashi_total(self):
        """貸方合計金額"""
        return self.meisai.filter(kari_kashi="SHI").aggregate(
            total=models.Sum("kingaku")
        )["total"] or Decimal("0")

    def validate_taisha_itchi(self):
        """貸借一致チェック: 借方合計 = 貸方合計"""
        kari = self.get_kari_total()
        kashi = self.get_kashi_total()
        if kari != kashi:
            diff = kari - kashi
            raise ValidationError(
                f"貸借が一致していません。差額: {diff:,.0f}円"
                f" (借方: {kari:,.0f} / 貸方: {kashi:,.0f})"
            )


class ShiwakeMeisai(BaseModel):
    """仕訳明細（明細行）"""

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
    kari_kashi = models.CharField(
        max_length=3, choices=KARI_KASHI_CHOICES, verbose_name="借/貸"
    )
    kamoku = models.ForeignKey(
        KanjoKamokuMaster,
        on_delete=models.PROTECT,
        verbose_name="勘定科目",
        limit_choices_to={"level": 4, "is_active": True},
    )
    bumon = models.ForeignKey(
        BumonMaster,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="部門",
        limit_choices_to={"is_active": True},
    )
    kingaku = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="金額")
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
        ordering = ["kari_kashi", "id"]

    def __str__(self):
        return f"{self.get_kari_kashi_display()} {self.kamoku} ¥{self.kingaku:,.0f}"
