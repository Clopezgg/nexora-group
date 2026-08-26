from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Modelo base que serializa a camelCase para el contrato con el frontend."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
