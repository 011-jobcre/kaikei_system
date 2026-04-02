from common.models import BaseModel
from django.db import models


class KanjoKamokuMaster(BaseModel):
    """勘定科目マスタ"""

    TAISHA_KUBUN_CHOICES = [
        ("SHISAN", "資産"),
        ("FUSAI", "負債"),
        ("JUNSHISAN", "純資産"),
        ("SHUEKI", "収益"),
        ("HIYO", "費用"),
    ]

    # 借方残高科目: 資産・費用 / 貸方残高科目: 負債・純資産・収益
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
            # 親がある場合は親のレベル+1
            self.level = self.parent.level + 1
            # 貸借区分が未設定なら親から継承
            self.taisha_kubun = self.parent.taisha_kubun
        else:
            # 親がない場合はレベル1
            self.level = 1
            # レベル1かつ貸借区分が未設定の場合、名称から推測
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
            "JUNSHISAN": "neutral",
            "SHUEKI": "error",
            "HIYO": "accent",
        }
        return keys.get(self.taisha_kubun, "neutral")


class BumonMaster(BaseModel):
    """部門マスタ"""

    code = models.CharField(max_length=10, unique=True, verbose_name="部門コード")
    name = models.CharField(max_length=100, verbose_name="部門名")
    manager_name = models.CharField(max_length=100, blank=True, verbose_name="担当者名")
    annual_budget = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="年間予算"
    )
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

    ZEI_KUBUN_CHOICES = [
        ("STANDARD", "課税（標準税率10%）"),
        ("REDUCED", "課税（軽減税率8%）"),
        ("EXEMPT", "非課税"),
        ("FREE", "免税"),
        ("OUTSIDE", "対象外"),
    ]

    zei_kubun = models.CharField(
        max_length=20,
        choices=ZEI_KUBUN_CHOICES,
        unique=True,
        verbose_name="税区分コード",
    )
    zei_name = models.CharField(max_length=100, verbose_name="税区分名")
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="税率(%)"
    )
    is_active = models.BooleanField(default=True, verbose_name="有効")
    valid_from = models.DateField(null=True, blank=True, verbose_name="適用開始日")
    valid_to = models.DateField(null=True, blank=True, verbose_name="適用終了日")
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
    name = models.CharField(max_length=200, verbose_name="取引先名")
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
