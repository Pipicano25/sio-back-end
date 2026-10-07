"""Esquemas de hitos y secuencias (`contracts/rest-api.md` rutas 13–19)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from purchase_service.api.schemas.purchases import StrictModel
from purchase_service.application.lifecycle_service import Timeline
from purchase_service.application.sequence_service import SequenceData, SequenceView
from purchase_service.domain.numbering import format_number, max_number_text_length, next_value
from purchase_service.infrastructure.models import PurchaseLifecycleEvent

EventType = Literal["ORDERED", "SUPPLIER_DISPATCHED", "ARRIVED", "RECEIVED", "AVAILABLE_FOR_SALE"]
Source = Literal["USER", "SUPPLIER", "INTEGRATION", "SYSTEM"]


class LifecycleEventIn(StrictModel):
    event_type: EventType
    occurred_at: AwareDatetime
    source: Source
    notes: Annotated[str, Field(max_length=2000)] | None = None


class LifecycleEventResponse(BaseModel):
    id: UUID
    purchase_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_by_user_id: UUID
    source: str
    notes: str | None
    created_at: datetime
    created_by: str
    is_current: bool | None = None

    @classmethod
    def of(cls, event: PurchaseLifecycleEvent, is_current: bool | None = None) -> LifecycleEventResponse:
        return cls(
            id=event.id,
            purchase_id=event.purchase_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            recorded_by_user_id=event.recorded_by_user_id,
            source=event.source,
            notes=event.notes,
            created_at=event.created_at,
            created_by=event.created_by,
            is_current=is_current,
        )


class IntervalResponse(BaseModel):
    from_event_type: str = Field(serialization_alias="from")
    to_event_type: str = Field(serialization_alias="to")
    hours: str


class TimelineResponse(BaseModel):
    items: list[LifecycleEventResponse]
    current: dict[str, UUID | None]
    intervals: list[IntervalResponse]
    total_lead_time_hours: str | None

    @classmethod
    def of(cls, timeline: Timeline) -> TimelineResponse:
        current_ids = set(timeline.current.values())
        return cls(
            items=[LifecycleEventResponse.of(event, event.id in current_ids) for event in timeline.events],
            current={
                event_type: timeline.current.get(event_type)
                for event_type in ("ORDERED", "SUPPLIER_DISPATCHED", "ARRIVED", "RECEIVED", "AVAILABLE_FOR_SALE")
            },
            intervals=[
                IntervalResponse(from_event_type=item.from_type, to_event_type=item.to_type, hours=str(item.hours))
                for item in timeline.intervals
            ],
            total_lead_time_hours=str(timeline.total_lead_time_hours) if timeline.total_lead_time_hours is not None else None,
        )


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
