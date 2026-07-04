"""Monkey-patch missing ``langchain_community.chat_models.vertexai`` module.

Ragas (v0.4.x) imports ``ChatVertexAI`` from ``langchain_community`` at module
top level, but newer versions of ``langchain-community`` no longer bundle the
Vertex AI integration. This module creates a stub so Ragas can load without
the optional Vertex AI dependency.
"""

import sys
from types import ModuleType

_MODULE_PATH = "langchain_community.chat_models.vertexai"

if _MODULE_PATH not in sys.modules:

    class _StubVertexAI:
        pass

    stub = ModuleType(_MODULE_PATH)
    stub.ChatVertexAI = _StubVertexAI
    sys.modules[_MODULE_PATH] = stub
