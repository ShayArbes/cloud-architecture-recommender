"""Parser selection — LLM-enriched when an API key is configured (CLAUDE.md §2)."""

import logging

from anthropic import AsyncAnthropic

from app.core.config import Settings
from app.scraper.llm_parser import ClaudeEnrichedParser
from app.scraper.parser import ArchitectureParser
from app.scraper.rules_parser import RulesBasedParser

logger = logging.getLogger(__name__)


def create_parser(settings: Settings) -> ArchitectureParser:
    """Return the Claude-enriched parser if a key is set, else the rules parser."""
    rules_parser = RulesBasedParser()
    if not settings.anthropic_api_key:
        logger.info("No ANTHROPIC_API_KEY configured — using rule-based parser")
        return rules_parser
    logger.info("ANTHROPIC_API_KEY configured — using Claude-enriched parser")
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return ClaudeEnrichedParser(client, rules_parser)
