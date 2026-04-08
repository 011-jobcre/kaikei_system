from common.models import BaseModel
from django.db import models
import datetime
from django.core.validators import MinValueValidator, MaxValueValidator


class KanjoKamokuMaster(BaseModel):
    """勘定科目マスタ"""

    TAISHA_KUBUN_CHOICES = [
        ("SHISAN", "資産"),
        ("FUSAI", "負債"),
        ("JUNSHISAN", "純資産"),
        ("SHUEKI", "収益"),
        ("HIYO", "費用"),
    ]

    # Debit-balance accounts: Assets & Expenses
    # Credit-balance accounts: Liabilities, Equity & Revenue
    KARI_ZANDAKA = {"SHISAN", "HIYO"}
    KASHI_ZANDAKA = {"FUSAI", "JUNSHISAN", "SHUEKI"}

    code = models.CharField(max_length=10, unique=True, verbose_name="科目コード")
    name = models.CharField(max_length=100, verbose_name="科目名")
    level = models.PositiveSmallIntegerField(verbose_name="レベル", blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="親科目",
    )
    taisha_kubun = models.CharField(
        max_length=20,
        choices=TAISHA_KUBUN_CHOICES,
        verbose_name="科目属性（貸借区分）",
        blank=True,
    )
    is_active = models.BooleanField(default=True, verbose_name="有効")

    class Meta:
        verbose_name = "勘定科目"
        verbose_name_plural = "勘定科目マスタ"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    def save(self, *args, **kwargs):
        """保存時にレベルと貸借区分を自動設定"""
        if self.parent:
            # If parent exists, set level = parent.level + 1
            self.level = self.parent.level + 1
            # Inherit taisha_kubun from parent if not set
            self.taisha_kubun = self.parent.taisha_kubun
        else:
            # No parent: set level to 1
            self.level = 1
            # If level 1 and taisha_kubun is unset, infer from the name
            if not self.taisha_kubun:
                name = self.name or ""
                if "資産" == name:
                    self.taisha_kubun = "SHISAN"
                elif "負債" == name:
                    self.taisha_kubun = "FUSAI"
                elif "純資産" == name or "資本" == name:
                    self.taisha_kubun = "JUNSHISAN"
                elif "収益" == name or "売上" == name:
                    self.taisha_kubun = "SHUEKI"
                elif "費用" == name or "原価" == name or "損失" == name:
                    self.taisha_kubun = "HIYO"

        super().save(*args, **kwargs)

    @property
    def is_kari_zandaka(self):
        """借方残高科目かどうか（資産・費用）"""
        return self.taisha_kubun in self.KARI_ZANDAKA

    @property
    def kubun_theme_key(self):
        """DaisyUI semantic color keys for themes"""
        keys = {
            "SHISAN": "primary",
            "FUSAI": "info",
            "JUNSHISAN": "success",
            "SHUEKI": "error",
            "HIYO": "warning",
        }
        return keys.get(self.taisha_kubun, "neutral")


class BumonMaster(BaseModel):
    """部門マスタ"""

    code = models.CharField(max_length=10, unique=True, verbose_name="部門コード")
    name = models.CharField(max_length=100, verbose_name="部門名")
    manager_name = models.CharField(max_length=100, blank=True, verbose_name="担当者名")
    annual_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="年間予算")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    order_no = models.PositiveIntegerField(default=0, verbose_name="表示順")

    class Meta:
        verbose_name = "部門"
        verbose_name_plural = "部門マスタ"
        ordering = ["order_no", "code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class ZeiMaster(BaseModel):
    """消費税率マスタ"""

    zei_name = models.CharField(max_length=100, verbose_name="税区分名")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="税率(%)")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    valid_from = models.DateField(
        null=True,
        blank=True,
        verbose_name="適用開始日",
        validators=[MinValueValidator(limit_value=datetime.date(1900, 1, 1))],
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="適用終了日",
        validators=[MaxValueValidator(limit_value=datetime.date(2100, 12, 31))],
    )
    order_no = models.PositiveIntegerField(default=0, verbose_name="表示順")

    class Meta:
        verbose_name = "税区分"
        verbose_name_plural = "消費税率マスタ"
        ordering = ["order_no"]

    def __str__(self):
        return self.zei_name


class TorihikiSakiMaster(BaseModel):
    """取引先マスタ（顧客・仕入先）"""

    code = models.CharField(max_length=10, unique=True, verbose_name="取引先コード")
    name = models.CharField(max_length=100, verbose_name="取引先名")
    address = models.TextField(blank=True, verbose_name="住所")
    phone = models.CharField(max_length=20, blank=True, verbose_name="電話番号")
    email = models.EmailField(blank=True, verbose_name="メールアドレス")
    is_active = models.BooleanField(default=True, verbose_name="有効")

    class Meta:
        verbose_name = "取引先"
        verbose_name_plural = "取引先マスタ"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"
