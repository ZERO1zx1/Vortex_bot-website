from src.cogs.shop.shop import SERVER_SHOP_ITEMS, SHOP_ITEMS


def test_server_shop_catalog_has_concrete_categories_and_unique_ids():
    ids = [item["id"] for item in SERVER_SHOP_ITEMS]
    assert len(ids) == len(set(ids))
    assert {item["category"] for item in SERVER_SHOP_ITEMS} == {
        "server_role", "boost", "server_access", "cosmetic", "utility"
    }
    assert {item["id"] for item in SERVER_SHOP_ITEMS} <= {item["id"] for item in SHOP_ITEMS}


def test_server_roles_have_a_resolvable_configuration_contract():
    role_items = [item for item in SERVER_SHOP_ITEMS if item["category"] in {"server_role", "server_access"}]
    assert all(item.get("role_name") or item.get("role_type") for item in role_items)
