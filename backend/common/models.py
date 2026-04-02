from django.db import models


class BaseModel(models.Model):
    """全モデル共通の抽象基底クラス"""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        abstract = True
