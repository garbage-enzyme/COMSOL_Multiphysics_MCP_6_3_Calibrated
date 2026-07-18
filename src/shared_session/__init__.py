"""Opt-in contracts for non-owning shared COMSOL Server sessions."""

from .contracts import (
    SHARED_SERVER_FEATURE_ENV,
    SHARED_SERVER_PROFILE,
    SharedServerFeatureGate,
    SharedServerEndpoint,
    normalize_shared_server_endpoint,
    normalize_shared_server_feature_gate,
)
from .identity import (
    AttachedServerIdentity,
    SharedModelSelector,
    normalize_attached_server_identity,
    normalize_shared_model_selector,
)
from .locking import (
    SharedModelIdentity,
    SharedModelLock,
    SharedModelRevision,
    build_shared_model_lock,
    build_shared_model_revision,
    normalize_shared_model_identity,
)

__all__ = [
    "SHARED_SERVER_FEATURE_ENV",
    "SHARED_SERVER_PROFILE",
    "AttachedServerIdentity",
    "SharedModelIdentity",
    "SharedModelLock",
    "SharedModelRevision",
    "SharedModelSelector",
    "SharedServerEndpoint",
    "SharedServerFeatureGate",
    "build_shared_model_lock",
    "build_shared_model_revision",
    "normalize_attached_server_identity",
    "normalize_shared_model_identity",
    "normalize_shared_model_selector",
    "normalize_shared_server_endpoint",
    "normalize_shared_server_feature_gate",
]
