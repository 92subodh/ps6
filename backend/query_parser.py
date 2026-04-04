"""Natural-language parser for What-If scenario queries."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import spacy
except Exception:  # noqa: BLE001
    spacy = None


class ScenarioQueryParser:
    """Extract structured attack intent from natural language queries."""

    STAGE_WORD_MAP = {
        "one": "P1",
        "two": "P2",
        "three": "P3",
        "four": "P4",
        "five": "P5",
        "six": "P6",
    }

    ATTACK_ALIASES = {
        "lstm_drift": [
            "drift",
            "slow drift",
            "gradual",
            "creeping",
            "stealth drift",
            "biased trend",
        ],
        "cgan_novel": [
            "spike",
            "burst",
            "novel",
            "outlier",
            "sudden anomaly",
            "injection spike",
        ],
        "vae_boundary": [
            "boundary",
            "replay",
            "mimic",
            "near normal",
            "edge attack",
            "boundary push",
        ],
    }

    SEVERITY_ALIASES = {
        "mild": ["mild", "light", "low", "minor"],
        "moderate": ["moderate", "medium", "avg", "average"],
        "severe": ["severe", "high", "critical", "extreme"],
    }

    def __init__(self) -> None:
        self._nlp = None
        self.backend = "regex"

        if spacy is not None:
            try:
                self._nlp = spacy.load("en_core_web_sm")
                self.backend = "spacy_sm"
            except Exception:  # noqa: BLE001
                self._nlp = spacy.blank("en")
                self.backend = "spacy_blank"

    def _tokenize(self, text: str) -> List[str]:
        if self._nlp is None:
            return re.findall(r"[a-z0-9_]+", text.lower())

        doc = self._nlp(text.lower())
        tokens = []
        for token in doc:
            if token.is_space:
                continue
            lemma = token.lemma_.strip().lower()
            tokens.append(lemma if lemma else token.text.lower())
        return tokens

    def _extract_stage(self, normalized: str, tokens: List[str]) -> Optional[str]:
        match = re.search(r"\bP\s*([1-6])\b", normalized, flags=re.IGNORECASE)
        if match:
            return "P%s" % match.group(1)

        match = re.search(r"\bstage\s*([1-6])\b", normalized, flags=re.IGNORECASE)
        if match:
            return "P%s" % match.group(1)

        for word, stage in self.STAGE_WORD_MAP.items():
            if re.search(r"\bstage\s+%s\b" % word, normalized, flags=re.IGNORECASE):
                return stage

        for token in tokens:
            if token in self.STAGE_WORD_MAP:
                maybe_stage = self.STAGE_WORD_MAP[token]
                if re.search(r"\b(?:p|stage)\s+%s\b" % token, normalized, flags=re.IGNORECASE):
                    return maybe_stage

        return None

    def _extract_attack_type(self, normalized: str, tokens: List[str]) -> Tuple[Optional[str], Optional[str]]:
        for attack_type, aliases in self.ATTACK_ALIASES.items():
            for alias in aliases:
                if re.search(r"\b%s\b" % re.escape(alias), normalized, flags=re.IGNORECASE):
                    return attack_type, alias

        token_set = set(tokens)
        if {"drift", "gradual"}.intersection(token_set):
            return "lstm_drift", "token_match"
        if {"spike", "burst", "novel"}.intersection(token_set):
            return "cgan_novel", "token_match"
        if {"boundary", "replay", "mimic"}.intersection(token_set):
            return "vae_boundary", "token_match"

        return None, None

    def _extract_severity(self, normalized: str, tokens: List[str]) -> Tuple[Optional[str], Optional[str]]:
        for severity, aliases in self.SEVERITY_ALIASES.items():
            for alias in aliases:
                if re.search(r"\b%s\b" % re.escape(alias), normalized, flags=re.IGNORECASE):
                    return severity, alias

        if "urgent" in tokens or "danger" in tokens:
            return "severe", "urgency_signal"
        return None, None

    def _extract_duration_seconds(self, normalized: str) -> Optional[int]:
        match = re.search(
            r"\b(\d+)\s*(second|seconds|sec|secs|minute|minutes|min|mins)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        value = int(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith("min"):
            value *= 60

        return max(20, min(360, value))

    def parse(self, query: str) -> Dict[str, Any]:
        normalized = query.strip()
        tokens = self._tokenize(normalized)

        stage = self._extract_stage(normalized, tokens)
        attack_type, attack_signal = self._extract_attack_type(normalized.lower(), tokens)
        severity, severity_signal = self._extract_severity(normalized.lower(), tokens)
        duration_seconds = self._extract_duration_seconds(normalized)

        confidence = 0.15
        if stage:
            confidence += 0.35
        if attack_type:
            confidence += 0.35
        if severity:
            confidence += 0.10
        if duration_seconds:
            confidence += 0.05

        confidence = round(min(0.98, confidence), 2)

        matched_phrases = [
            phrase
            for phrase in [
                stage,
                attack_signal,
                severity_signal,
            ]
            if phrase
        ]

        return {
            "stage": stage,
            "attack_type": attack_type,
            "severity": severity,
            "duration_seconds": duration_seconds,
            "confidence": confidence,
            "parser_backend": self.backend,
            "matched_phrases": matched_phrases,
            "tokens": tokens[:40],
        }
