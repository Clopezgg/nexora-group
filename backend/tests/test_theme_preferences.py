from tests.helpers import create_company, login_admin


def test_user_preferences_roundtrip_and_company_default(client, db_session):
    login_admin(client)
    company = create_company(client)

    # Default: sin preferencia de usuario.
    initial = client.get("/api/me/preferences")
    assert initial.status_code == 200, initial.text
    assert initial.json() == {"themeId": None, "density": None}

    # La compañía fija su default (lo expone CompanyResponse; el frontend lo
    # resuelve, no /me/preferences).
    patched = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"defaultThemeId": "quartz-light", "defaultDensity": "compact"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["defaultThemeId"] == "quartz-light"
    assert patched.json()["defaultDensity"] == "compact"

    companies = client.get("/api/master-data/companies").json()
    this_company = next(c for c in companies if c["id"] == company["id"])
    assert this_company["defaultThemeId"] == "quartz-light"

    # El usuario sobreescribe su preferencia.
    put = client.put(
        "/api/me/preferences", json={"themeId": "nexora-dark", "density": "comfortable"}
    )
    assert put.status_code == 200, put.text
    assert put.json() == {"themeId": "nexora-dark", "density": "comfortable"}

    assert client.get("/api/me/preferences").json() == {
        "themeId": "nexora-dark",
        "density": "comfortable",
    }


def test_user_preferences_rejects_invalid_density(client, db_session):
    login_admin(client)
    bad = client.put("/api/me/preferences", json={"density": "gigante"})
    assert bad.status_code == 422, bad.text


def test_user_preferences_accepts_finance_dense_density(client, db_session):
    """Enterprise Theme Architecture §8: la densidad Finance Dense es válida."""
    login_admin(client)
    ok = client.put(
        "/api/me/preferences", json={"themeId": "nexora-executive", "density": "finance-dense"}
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["density"] == "finance-dense"
