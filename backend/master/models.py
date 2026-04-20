# =========================================================
# Master Models
# =========================================================

import datetime
from common.models import BaseModel
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class KanjoKamokuMaster(BaseModel):
    """Account Master"""

    TAISHA_KUBUN_CHOICES = [
        ("SHISAN", "資産"),
        ("FUSAI", "負債"),
        ("JUNSHISAN", "純資産"),
        ("SHUEKI", "収益"),
        ("HIYO", "費用"),
    ]

    # Debit-balance accounts: 資産: Assets, 費用: Expenses
    # Credit-balance accounts: 負債: Liabilities, 純資産: Equity, 収益: Revenue
    KARI_ZANDAKA = {"SHISAN", "HIYO"}
    KASHI_ZANDAKA = {"FUSAI", "JUNSHISAN", "SHUEKI"}

    code = models.CharField(verbose_name="勘定科目コード", max_length=10, unique=True)
    name = models.CharField(verbose_name="勘定科目名", max_length=100)
    furigana = models.CharField(verbose_name="フリガナ", max_length=100, blank=True, help_text="ローマ字検索用")
    level = models.PositiveSmallIntegerField(verbose_name="レベル", blank=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="親勘定科目",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )
    taisha_kubun = models.CharField(verbose_name="貸借区分", max_length=20, choices=TAISHA_KUBUN_CHOICES, blank=True)
    is_active = models.BooleanField(verbose_name="有効", default=True)

    class Meta:
        verbose_name = "勘定科目マスタ"
        verbose_name_plural = "勘定科目マスタ"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    def save(self, *args, **kwargs):
        """Automatically sets level and debit/credit status on save"""
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
        """Returns true if the account is a debit-balance account (Assets/Expenses)"""
        return self.taisha_kubun in self.KARI_ZANDAKA

    @property
    def kubun_theme_key(self):
        """DaisyUI semantic color keys for themes"""
        keys = {
            "SHISAN": "level-1",
            "FUSAI": "level-2",
            "JUNSHISAN": "level-3",
            "SHUEKI": "level-4",
            "HIYO": "level-5",
        }
        return keys.get(self.taisha_kubun, "neutral")


class HojoKamokuMaster(BaseModel):
    """Sub-account Master — provides finer detail beneath a main account.
    Examples:
        - Bank account: 普通預金 → みずほ銀行, 三菱UFJ銀行
        - Expense type: 旅費交通費 → 電車代, タクシー代
    """

    kamoku = models.ForeignKey(
        KanjoKamokuMaster,
        verbose_name="勘定科目",
        on_delete=models.CASCADE,
        related_name="hojo_set",
        limit_choices_to={"level": 4, "is_active": True},
    )
    code = models.CharField(verbose_name="補助科目コード", max_length=10)
    name = models.CharField(verbose_name="補助科目名", max_length=100)
    furigana = models.CharField(verbose_name="フリガナ", max_length=100, blank=True, help_text="ローマ字検索用")
    is_active = models.BooleanField(verbose_name="有効", default=True)

    class Meta:
        verbose_name = "補助科目マスタ"
        verbose_name_plural = "補助科目マスタ"
        ordering = ["kamoku__code", "code"]
        # Code must be unique within the parent account
        unique_together = [["kamoku", "code"]]

    def __str__(self):
        return f"{self.kamoku.code}-{self.code} {self.name}"


class BumonMaster(BaseModel):
    """Department Master"""

    code = models.CharField(verbose_name="部門コード", max_length=10, unique=True)
    name = models.CharField(verbose_name="部門名", max_length=100)
    manager_name = models.CharField(verbose_name="担当者名", max_length=100, blank=True)
    annual_budget = models.DecimalField(verbose_name="年間予算", max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(verbose_name="有効", default=True)

    class Meta:
        verbose_name = "部門マスタ"
        verbose_name_plural = "部門マスタ"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class ZeiMaster(BaseModel):
    """Consumption Tax Rate Master"""

    zei_name = models.CharField(verbose_name="税区分名", max_length=100)
    tax_rate = models.DecimalField(verbose_name="税率（%）", max_digits=5, decimal_places=2, default=0)
    valid_from = models.DateField(
        verbose_name="適用開始日",
        validators=[MinValueValidator(limit_value=datetime.date(1900, 1, 1))],
        null=True,
        blank=True,
    )
    valid_to = models.DateField(
        verbose_name="適用終了日",
        validators=[MaxValueValidator(limit_value=datetime.date(2100, 12, 31))],
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(verbose_name="有効", default=True)
    order_no = models.PositiveIntegerField(verbose_name="表示順", default=0)

    class Meta:
        verbose_name = "税マスタ"
        verbose_name_plural = "税マスタ"
        ordering = ["order_no"]

    def __str__(self):
        return self.zei_name

    def save(self, *args, **kwargs):
        if not self.order_no:
            max_order_no = ZeiMaster.objects.aggregate(models.Max("order_no"))["order_no__max"]
            self.order_no = max_order_no + 1 if max_order_no else 1
        super().save(*args, **kwargs)


class TorihikiSakiMaster(BaseModel):
    """Business Partner Master (Customers / Suppliers)"""

    code = models.CharField(verbose_name="取引先コード", max_length=10, unique=True)
    name = models.CharField(verbose_name="取引先名", max_length=100)
    address = models.TextField(verbose_name="住所", blank=True)
    phone = models.CharField(verbose_name="電話番号", max_length=20, blank=True)
    email = models.EmailField(verbose_name="メールアドレス", blank=True)
    is_active = models.BooleanField(verbose_name="有効", default=True)

    class Meta:
        verbose_name = "取引先マスタ"
        verbose_name_plural = "取引先マスタ"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"
