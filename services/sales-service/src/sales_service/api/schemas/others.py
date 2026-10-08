"""Esquemas de secuencias (`contracts/rest-api.md` rutas 14–18)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from sales_service.api.schemas.sales import StrictModel
from sales_service.application.sequence_service import SequenceData, SequenceView
from sales_service.domain.numbering import format_number, max_number_text_length, next_value

class SequenceIn(StrictModel):
    branch_id: UUID | None = None
    series_code: Annotated[str, Field(pattern=r"^[A-Z0-9_-]{1,40}$")]
    prefix: Annotated[str, Field(pattern=r"^[A-Z0-9]{1,20}$")]
    separator: Literal["-", "/", ".", "_", ""]
    initial_number: Annotated[int, Field(ge=1, le=10**17)]
    maximum_number: Annotated[int, Field(ge=1, le=10**18 - 1)] | None = None
    number_length: Annotated[int, Field(ge=1, le=18)]
    reset_policy: Literal["NEVER", "YEARLY", "MONTHLY"]

    @model_validator(mode="after")
    def _coherent(self):
        if self.maximum_number is not None and self.maximum_number < self.initial_number:
            raise PydanticCustomError("INVALID_FORMAT", "maximum_number no puede ser menor que initial_number.")
        if max_number_text_length(self.prefix, self.separator, self.number_length) > 80:
            raise PydanticCustomError("INVALID_FORMAT", "El número resultante superaría 80 caracteres.")
        return self

    def to_data(self) -> SequenceData:
        return SequenceData(
            branch_id=self.branch_id,
            series_code=self.series_code,
            prefix=self.prefix,
            separator=self.separator,
            initial_number=self.initial_number,
            maximum_number=self.maximum_number,
            number_length=self.number_length,
            reset_policy=self.reset_policy,
        )


class SequenceUpdateIn(SequenceIn):
    version: Annotated[int, Field(ge=1)]


class CounterResponse(BaseModel):
    period_key: str
    current_number: int
    next_number_preview: str


class SequenceResponse(BaseModel):
    id: UUID
    company_id: UUID
    branch_id: UUID | None
    document_kind: str
    series_code: str
    prefix: str
    separator: str
    initial_number: int
    maximum_number: int | None
    number_length: int
    reset_policy: str
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    counters: list[CounterResponse]

    @classmethod
    def of(cls, view: SequenceView) -> SequenceResponse:
        sequence = view.sequence
        return cls(
            id=sequence.id,
            company_id=sequence.company_id,
            branch_id=sequence.branch_id,
            document_kind=sequence.document_kind,
            series_code=sequence.series_code,
            prefix=sequence.prefix,
            separator=sequence.separator,
            initial_number=sequence.initial_number,
            maximum_number=sequence.maximum_number,
            number_length=sequence.number_length,
            reset_policy=sequence.reset_policy,
            is_active=sequence.is_active,
            version=sequence.version,
            created_at=sequence.created_at,
            updated_at=sequence.updated_at,
            created_by=sequence.created_by,
            updated_by=sequence.updated_by,
            counters=[
                CounterResponse(
                    period_key=counter.period_key,
                    current_number=counter.current_number,
                    next_number_preview=format_number(
                        sequence.prefix,
                        sequence.separator,
                        counter.period_key,
                        next_value(counter.current_number, sequence.initial_number),
                        sequence.number_length,
                    ),
                )
                for counter in view.counters
            ],
        )


class SequenceList(BaseModel):
    items: list[SequenceResponse]
