"""Optional Claude-API parser enriching characteristics extraction (S1.3).

The Claude API is used *only* for parsing/enrichment — never for scoring
(CLAUDE.md §6.3). This parser sits behind the same ``ArchitectureParser``
protocol as the rules parser, is constructed only when an API key is
configured, and falls back to the deterministic rules result on any LLM
failure so a scrape job never depends on the LLM being available.
"""

import logging

from anthropic import AsyncAnthropic

from app.models.architecture import ArchitectureCharacteristics, ParsedArchitecture
from app.scraper.rules_parser import RulesBasedParser

logger = logging.getLogger(__name__)

LLM_PARSER_VERSION = "llm-claude-sonnet-5-v1"

# claude-sonnet-5 is mandated by CLAUDE.md §2 for AI parsing.
_CLAUDE_MODEL = "claude-sonnet-5"
_MAX_TOKENS = 2048

_SYSTEM_PROMPT = (
    "You classify AWS reference architectures onto fixed capability dimensions. "
    "Given an architecture's title, description, and detected AWS services, "
    "return the characteristics object describing which workloads the design "
    "serves well. List-valued dimensions must include every value the design "
    "suits; scalar dimensions hold the strongest tier it serves well. "
    "Base your answer only on the provided content."
)


class ClaudeEnrichedParser:
    """Rules-based extraction with Claude-inferred characteristics on top."""

    parser_version = LLM_PARSER_VERSION

    def __init__(self, client: AsyncAnthropic, rules_parser: RulesBasedParser) -> None:
        self._client = client
        self._rules_parser = rules_parser

    async def parse(self, raw_html: str, source_url: str) -> ParsedArchitecture:
        """Parse with rules, then replace characteristics with Claude's inference.

        Any LLM failure (network, refusal, unparseable output) is logged and the
        deterministic rules result is returned unchanged — the fallback contract
        of CLAUDE.md §2.
        """
        base = await self._rules_parser.parse(raw_html, source_url)
        try:
            characteristics = await self._infer_characteristics(base)
        except Exception:
            logger.warning(
                "Claude enrichment failed for %s; keeping rule-based characteristics",
                source_url,
                exc_info=True,
            )
            return base
        return base.model_copy(
            update={
                "characteristics": characteristics,
                "use_cases": characteristics.use_cases,
                "parser_version": self.parser_version,
            }
        )

    async def _infer_characteristics(self, base: ParsedArchitecture) -> ArchitectureCharacteristics:
        """Ask Claude for the 9-dimension classification via structured outputs."""
        services = ", ".join(service.name for service in base.aws_services) or "none detected"
        response = await self._client.messages.parse(
            model=_CLAUDE_MODEL,
            max_tokens=_MAX_TOKENS,
            # Deterministic extraction task — thinking adds latency, not accuracy.
            thinking={"type": "disabled"},
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Title: {base.title}\n"
                        f"Description: {base.description}\n"
                        f"AWS services: {services}"
                    ),
                }
            ],
            output_format=ArchitectureCharacteristics,
        )
        if response.parsed_output is None:
            raise ValueError("Claude returned no parseable characteristics object")
        return response.parsed_output
