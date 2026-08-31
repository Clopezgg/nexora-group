from app.schemas.base import CamelModel


class UserPreferencesResponse(CamelModel):
    """Preferencias de UI del usuario. SOLO presentación (orden maestra §68).

    El default de la compañía NO se resuelve aquí: el frontend lo toma del
    objeto de la compañía activa (`CompanyResponse.defaultThemeId` /
    `defaultDensity`) y aplica la cascada usuario > compañía > 'nexora-classic'.
    """

    theme_id: str | None = None
    density: str | None = None


class UserPreferencesUpdate(CamelModel):
    theme_id: str | None = None
    density: str | None = None
