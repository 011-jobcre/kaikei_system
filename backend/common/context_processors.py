def rbac(request):
    """
    Context processor to make user roles available in all templates
    as `is_admin` and `is_accountant`.
    """
    if not request.user.is_authenticated:
        return {"is_admin": False, "is_accountant": False}

    groups = request.user.groups.values_list("name", flat=True)
    is_admin = request.user.is_superuser or request.user.is_staff or "Admins" in groups
    is_accountant = is_admin or "Accountants" in groups

    return {
        "is_admin": is_admin,
        "is_accountant": is_accountant,
    }
