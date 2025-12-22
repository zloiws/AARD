import os
import pytest

BASE = os.path.dirname(os.path.dirname(__file__))
SERVICES_DIR = os.path.join(BASE, "..", "docs", "services")

EXPECTED = [
    "ApplicationCore.md",
    "HTTPAPILayer.md",
    "DataORMLayer.md",
    "BusinessServices.md",
    "AgentsAndPlanning.md",
    "DecisionComponents.md",
    "ToolsExternalIntegrations.md",
    "RegistryServiceDiscovery.md",
    "SecurityAuthPermissions.md",
    "MemoryConversationStorage.md",
    "OpsMigrations.md",
    "UtilitiesObservability.md",
]


def test_service_docs_exist():
    base = os.path.join(os.path.dirname(__file__), "..", "docs", "services")
    base = os.path.normpath(base)
    missing = []
    for fn in EXPECTED:
        path = os.path.join(base, fn)
        if not os.path.exists(path):
            missing.append(fn)
    assert not missing, f"Missing service docs: {missing}"


