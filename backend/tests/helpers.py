from app.repositories import role_repository, user_repository
from app.security.passwords import hash_password
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD


def login_admin(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text


def create_user_with_role(db_session, *, email: str, role_name: str, password: str = "Passw0rd!23"):
    role = role_repository.get_by_name(db_session, role_name)
    assert role is not None, f"role {role_name} no existe (ejecuta ensure_base_roles)"
    user = user_repository.create_user(
        db_session,
        email=email,
        full_name="Usuario de prueba",
        password_hash=hash_password(password),
    )
    role_repository.assign_role(db_session, user_id=user.id, role_id=role.id)
    db_session.commit()
    return user


def login_as(client, *, email: str, password: str = "Passw0rd!23") -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def create_company(client, *, name: str = "Constructora Nexora", currency: str = "HNL") -> dict:
    response = client.post(
        "/api/master-data/companies",
        json={"name": name, "functionalCurrencyCode": currency},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_account(client, *, company_id: str, code: str, name: str, account_type: str) -> dict:
    response = client.post(
        "/api/master-data/accounts",
        json={"companyId": company_id, "code": code, "name": name, "accountType": account_type},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_supplier(client, *, company_id: str, legal_name: str = "Proveedor de prueba") -> dict:
    response = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": legal_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_treasury_account(
    client, *, company_id: str, gl_account_id: str, name: str = "Banco Principal", kind: str = "BANK"
) -> dict:
    response = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": company_id,
            "name": name,
            "kind": kind,
            "currencyCode": "HNL",
            "glAccountId": gl_account_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
