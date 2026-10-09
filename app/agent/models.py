from enum import Enum
from pydantic import BaseModel, Field

class PlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class PlanStep(BaseModel):
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING

class Plan(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list)
    current_step: int = 0

class IterationStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class ChatMessage(BaseModel):
    role: str
    content: str

class Agentstate(BaseModel):
    goal: str
    status: IterationStatus = IterationStatus.RUNNING
    plan: Plan = Field(default_factory=Plan)
    message: list[ChatMessage] = Field(default_factory=list)
    Iteration: int = 0
