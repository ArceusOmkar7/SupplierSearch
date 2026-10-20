"""Explicit model registration; importing never runs migrations or connects to a database."""

from verisource.db.models.actions import HumanAction
from verisource.db.models.artifacts import CheckAttempt, DocumentArtifact, Extraction
from verisource.db.models.assessments import AssessmentSnapshot, SupplierDecision
from verisource.db.models.cases import (
    Case,
    CaseCreationReceipt,
    IdentityResolution,
    RequirementRevision,
    Supplier,
    SupplierSite,
)
from verisource.db.models.conversation import ConversationMessage
from verisource.db.models.datasets import QcoRecord, SourceDataset, SourceDatasetRecord
from verisource.db.models.deletion import DeletionRequest, LocalSnapshot
from verisource.db.models.evidence import Assessment, EvidenceRecord, EvidenceUse
from verisource.db.models.identity import BuyerAccount, LoginSession
from verisource.db.models.reports import Report
from verisource.db.models.sources import (
    BudgetReservation,
    ProviderAccount,
    SourceAuthorization,
    SourceDefinition,
)
from verisource.db.models.verification import ChecklistVersion, CheckTask, Claim, VerificationRun
from verisource.db.models.work import CaseEvent, GraphCheckpointReference, WorkItem

__all__ = [
    "Assessment",
    "AssessmentSnapshot",
    "BudgetReservation",
    "BuyerAccount",
    "Case",
    "CaseCreationReceipt",
    "CaseEvent",
    "CheckAttempt",
    "CheckTask",
    "ChecklistVersion",
    "Claim",
    "ConversationMessage",
    "DeletionRequest",
    "DocumentArtifact",
    "EvidenceRecord",
    "EvidenceUse",
    "Extraction",
    "GraphCheckpointReference",
    "HumanAction",
    "IdentityResolution",
    "LocalSnapshot",
    "LoginSession",
    "ProviderAccount",
    "QcoRecord",
    "Report",
    "RequirementRevision",
    "SourceAuthorization",
    "SourceDataset",
    "SourceDatasetRecord",
    "SourceDefinition",
    "Supplier",
    "SupplierDecision",
    "SupplierSite",
    "VerificationRun",
    "WorkItem",
]
