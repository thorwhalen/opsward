"""Diagnose, generate, and maintain the AI agent setup of your projects."""

from opsward.base import (
    AgentInfo,
    ComponentScore,
    DiagnosisReport,
    DocSpec,
    GeneratedFile,
    MaintenanceSuggestion,
    ProjectType,
    RuleInfo,
    ScanResult,
    SkillInfo,
)
from opsward.scan import scan
from opsward.score import diagnose, validate_skill_spec
from opsward.generate import generate, generate_skills
from opsward.maintain import maintain
from opsward.recommend import recommend_skills, SkillRecommendation
