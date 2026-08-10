"""Composition root — the only module permitted to know about every layer at once.

Wires infrastructure adapters into application ports and hands the assembled
use cases to the CLI. Populated as later milestones add infrastructure adapters
(M2: agent gateway; M3: capacity probe/notifier; M4: REST API gateway).
"""

from __future__ import annotations
