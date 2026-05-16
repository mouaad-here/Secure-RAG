"""
Secure RAG MVP — Security Patterns
Central repository for regex patterns used to detect prompt injections,
jailbreaks, and system prompt leaks.
"""

import re

# =============================================================================
# INPUT SCANNER PATTERNS
# =============================================================================

# Direct injection (imperative instructions to the LLM)
DIRECT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"forget\s+(everything|all|your)\s+(you|instructions?|rules?)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"new\s+instructions?:", re.I),
    re.compile(r"system\s*prompt:", re.I),
    re.compile(r"override\s+(previous|all|system)", re.I),
]

# Indirect injection (hidden instructions in document text)
INDIRECT_INJECTION_PATTERNS = [
    re.compile(r"when\s+asked\s+about\s+.+,?\s+(respond|say|answer|reply)\s+with", re.I),
    re.compile(r"always\s+(respond|say|answer|reply)\s+(with|that)", re.I),
    re.compile(r"if\s+(the\s+)?user\s+asks?\s+", re.I),
    re.compile(r"instead\s+of\s+.+,?\s+(say|respond|answer)", re.I),
]

# Jailbreak patterns (roleplay, persona switching)
JAILBREAK_PATTERNS = [
    re.compile(r"(pretend|imagine|act\s+as\s+if)\s+you\s+are", re.I),
    re.compile(r"roleplay\s+as", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"DAN\s+mode", re.I),
    re.compile(r"developer\s+mode\s+(enabled|on)", re.I),
]

# =============================================================================
# OUTPUT FIREWALL PATTERNS
# =============================================================================

# System prompt leakage detection
LEAKED_INSTRUCTION_PATTERNS = [
    re.compile(r"(my|the)\s+(system\s+)?instructions?\s+(are|say|tell)", re.I),
    re.compile(r"I\s+(am|was)\s+(instructed|told|programmed)\s+to", re.I),
    re.compile(r"my\s+prompt\s+(is|says|contains)", re.I),
    re.compile(r"STRICT\s+RULES", re.I),
    re.compile(r"NEVER\s+VIOLATE", re.I),
]
