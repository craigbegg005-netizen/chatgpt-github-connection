"""Optional local integrations. Not automatically connected or network-exposed."""

from .local_inference import LocalInference
from .local_search import LocalSearch
from .loopback_http import IntegrationUnavailable

__all__ = ["LocalInference", "LocalSearch", "IntegrationUnavailable"]
