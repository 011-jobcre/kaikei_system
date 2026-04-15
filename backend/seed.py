import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from master.models import KanjoKamokuMaster, ZeiMaster


def create_kamoku(code, name, parent=None):
    """
    Create or update an account title (kamoku).
    Do not pass `level` or `taisha_kubun` explicitly — rely on the automatic
    logic implemented in the model's overridden `save()` method.
    """
    obj, created = KanjoKamokuMaster.objects.get_or_create(code=code, defaults={"name": name, "parent": parent})
    if not created:
        obj.name = name
        obj.parent = parent
        obj.save()
    else:
        # Explicitly call save on creation to trigger model logic (just in case)
        obj.save()
    return obj


print("Seeding Zei Master...")
ZeiMaster.objects.get_or_create(
    zei_name="課税（標準税率10%）",
    defaults={
        "tax_rate": 10,
        "valid_from": "2019-10-01",
        "valid_to": "2030-09-30",
        "order_no": 2,
        "is_active": True,
    },
)
ZeiMaster.objects.get_or_create(
    zei_name="課税（軽減税率8%）",
    defaults={
        "tax_rate": 8,
        "valid_from": "2019-10-01",
        "valid_to": "2030-09-30",
        "order_no": 3,
        "is_active": True,
    },
)
ZeiMaster.objects.get_or_create(
    zei_name="非課税",
    defaults={
        "tax_rate": 0,
        "valid_from": "2019-10-01",
        "valid_to": "2030-09-30",
        "order_no": 5,
        "is_active": True,
    },
)
ZeiMaster.objects.get_or_create(
    zei_name="免税",
    defaults={
        "tax_rate": 0,
        "valid_from": "2019-10-01",
        "valid_to": "2030-09-30",
        "order_no": 4,
        "is_active": True,
    },
)
ZeiMaster.objects.get_or_create(
    zei_name="対象外",
    defaults={
        "tax_rate": 0,
        "valid_from": "2019-10-01",
        "valid_to": "2030-09-30",
        "order_no": 1,
        "is_active": True,
    },
)

print("Seeding KanjoKamoku Master (Levels 1-4)...")

# --- 1. Assets ---
shisan = create_kamoku("1", "資産")

# 1.1 Current Assets
ryudo_shisan = create_kamoku("11", "流動資産", parent=shisan)

# Level 3
genkin_yokin_grp = create_kamoku("111", "現金及び預金", parent=ryudo_shisan)

# Level 4
create_kamoku("111010", "現金", parent=genkin_yokin_grp)
create_kamoku("111020", "普通預金", parent=genkin_yokin_grp)
create_kamoku("111030", "当座預金", parent=genkin_yokin_grp)

# Level 3
urikake_grp = create_kamoku("112", "売上債権", parent=ryudo_shisan)

# Level 4
create_kamoku("112010", "売掛金", parent=urikake_grp)
create_kamoku("112020", "受取手形", parent=urikake_grp)

# Level 3
tanaoroshi_grp = create_kamoku("113", "棚卸資産", parent=ryudo_shisan)

# Level 4
create_kamoku("113010", "商品", parent=tanaoroshi_grp)
create_kamoku("113020", "製品", parent=tanaoroshi_grp)

# 1.2 Fixed Assets
kotei_shisan = create_kamoku("12", "固定資産", parent=shisan)

# Level 3
yukei_kotei_grp = create_kamoku("121", "有形固定資産", parent=kotei_shisan)

# Level 4
create_kamoku("121010", "建物", parent=yukei_kotei_grp)
create_kamoku("121020", "車両運搬具", parent=yukei_kotei_grp)
create_kamoku("121030", "備品", parent=yukei_kotei_grp)
create_kamoku("121040", "土地", parent=yukei_kotei_grp)
create_kamoku("121050", "工具器具備品", parent=yukei_kotei_grp)

# Level 3
kotei_shisan_kumikae = create_kamoku("122", "減価償却累計額", parent=kotei_shisan)

# Level 4
create_kamoku("122010", "建物減価償却累計額", parent=kotei_shisan_kumikae)
create_kamoku("122020", "車両運搬具減価償却累計額", parent=kotei_shisan_kumikae)
create_kamoku("122030", "備品減価償却累計額", parent=kotei_shisan_kumikae)

# --- 2. Liabilities ---
fusai = create_kamoku("2", "負債")

# 2.1 Current Liabilities
ryudo_fusai = create_kamoku("21", "流動負債", parent=fusai)

# Level 3
shiire_saimu_grp = create_kamoku("211", "仕入債務", parent=ryudo_fusai)

# Level 4
create_kamoku("211010", "買掛金", parent=shiire_saimu_grp)
create_kamoku("211020", "支払手形", parent=shiire_saimu_grp)

# Level 3
mibarai_grp = create_kamoku("212", "未払金・預り金", parent=ryudo_fusai)

# Level 4
create_kamoku("212010", "未払金", parent=mibarai_grp)
create_kamoku("212020", "預り金", parent=mibarai_grp)
create_kamoku("212030", "未払消費税等", parent=mibarai_grp)

# 2.2 Long-term Liabilities
kotei_fusai = create_kamoku("22", "固定負債", parent=fusai)

# Level 3
create_kamoku(
    "221010",
    "長期借入金",
    parent=create_kamoku("221", "長期借入金等", parent=kotei_fusai),
)

# --- 3. Equity ---
junshisan = create_kamoku("3", "純資産")

# 3.1
shihon = create_kamoku("31", "株主資本", parent=junshisan)

# Level 3
shihonkin_grp = create_kamoku("311", "資本金", parent=shihon)

# Level 4
create_kamoku("311010", "資本金", parent=shihonkin_grp)

# Level 3
rieki_grp = create_kamoku("312", "利益剰余金", parent=shihon)

# Level 4
create_kamoku("312010", "繰越利益剰余金", parent=rieki_grp)

# --- 4. Revenue ---
shueki = create_kamoku("4", "収益")

# 4.1
uriage_grp_parent = create_kamoku("41", "売上高", parent=shueki)

# Level 3
uriage_grp = create_kamoku("411", "売上高", parent=uriage_grp_parent)

# Level 4
create_kamoku("411010", "売上高", parent=uriage_grp)
create_kamoku("411020", "雑収入", parent=uriage_grp)

# 4.2
non_op_income = create_kamoku("42", "営業外収益", parent=shueki)

# Level 3
interest_grp = create_kamoku("421", "受取利息等", parent=non_op_income)

# Level 4
create_kamoku("421010", "受取利息", parent=interest_grp)

# --- 5. Expenses ---
hiyo = create_kamoku("5", "費用")

# 5.1 Cost of Goods Sold
genka = create_kamoku("51", "売上原価", parent=hiyo)

# Level 3
shiire_grp = create_kamoku("511", "仕入高", parent=genka)

# Level 4
create_kamoku("511010", "仕入高", parent=shiire_grp)
create_kamoku("511020", "外注費", parent=shiire_grp)

# 5.2 Selling, General & Administrative Expenses
hankan = create_kamoku("52", "販売費及び一般管理費", parent=hiyo)

# Level 3: Personnel Expenses
jinken_grp = create_kamoku("521", "人件費", parent=hankan)

# Level 4
create_kamoku("521010", "役員報酬", parent=jinken_grp)
create_kamoku("521020", "給与手当", parent=jinken_grp)
create_kamoku("521030", "法定福利費", parent=jinken_grp)
create_kamoku("521040", "福利厚生費", parent=jinken_grp)

# Level 3: Office & Other Expenses
jimu_grp = create_kamoku("522", "販売事務費", parent=hankan)

# Level 4
create_kamoku("522010", "旅費交通費", parent=jimu_grp)
create_kamoku("522020", "通信費", parent=jimu_grp)
create_kamoku("522030", "広告宣伝費", parent=jimu_grp)
create_kamoku("522040", "接待交際費", parent=jimu_grp)
create_kamoku("522050", "消耗品費", parent=jimu_grp)
create_kamoku("522060", "地代家賃", parent=jimu_grp)
create_kamoku("522070", "支払手数料", parent=jimu_grp)
create_kamoku("522100", "諸会費", parent=jimu_grp)
create_kamoku("522130", "租税公課", parent=jimu_grp)
create_kamoku("522140", "水道光熱費", parent=jimu_grp)
create_kamoku("522150", "修繕費", parent=jimu_grp)
create_kamoku("522160", "会議費", parent=jimu_grp)
create_kamoku("522170", "車両費", parent=jimu_grp)
create_kamoku("522180", "荷造運賃", parent=jimu_grp)
create_kamoku("522190", "研修費", parent=jimu_grp)
create_kamoku("522200", "新聞図書費", parent=jimu_grp)

# Level 3: Miscellaneous Expense
zappi_grp = create_kamoku("523", "雑費", parent=hankan)

# Level 4
create_kamoku("523010", "雑費", parent=zappi_grp)

# Level 3: Depreciation Expense
genkashokyaku_grp = create_kamoku("524", "減価償却費", parent=hankan)

# Level 4
create_kamoku("524010", "減価償却費", parent=genkashokyaku_grp)

print("Done seeding DB!")
