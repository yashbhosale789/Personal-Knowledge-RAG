import re

INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", "direct_override"),
    (r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", "direct_override"),
    (r"\[\s*(system|end of context|end context)\s*\]", "fake_structural_tag"),
    (r"\b(assistant|system)\s*:", "fake_role_label"),
    (r"supersedes?\s+all\s+(other\s+)?instructions?", "authority_hijack"),
    (r"you must (include|output|say|respond with)", "imperative_directive"),
]