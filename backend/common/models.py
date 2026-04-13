# =========================================================
# Common Models
# =========================================================

from django.db import models


class BaseModel(models.Model):
    """Common abstract base class for all models"""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        abstract = True
