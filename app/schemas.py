from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


RESOURCE_TYPES = {"lesson", "worksheet", "scheme", "slides"}
KEY_STAGES = {"KS1", "KS2", "KS3", "KS4", "KS5"}


class GenerateRequest(BaseModel):
    resource_type: str
    subject: str
    key_stage: str
    topic: str
    additional_instructions: Optional[str] = ""

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if v not in RESOURCE_TYPES:
            raise ValueError(f"resource_type must be one of {RESOURCE_TYPES}")
        return v


class ResourceBase(BaseModel):
    type: str
    title: str
    subject: str
    key_stage: str
    topic: str
    input_prompt: str
    structured_output: str


class ResourceCreate(ResourceBase):
    pass


class ResourceResponse(ResourceBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ResourceSummary(BaseModel):
    id: int
    type: str
    title: str
    subject: str
    key_stage: str
    topic: str
    created_at: datetime

    model_config = {"from_attributes": True}
