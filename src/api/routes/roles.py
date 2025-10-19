"""
Roles API Routes
Handles role-related endpoints (previewing roles, role templates)
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger

from ...camel_engine.role_creator import RoleCreator, RoleDefinition
from ...camel_engine.llm_provider import OpenRouterClient
from ...utils.config import settings


router = APIRouter()
llm_client = OpenRouterClient(api_key=settings.OPENROUTER_API_KEY)
role_creator = RoleCreator(llm_client=llm_client)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PreviewRolesRequest(BaseModel):
    """Request to preview roles for a topic"""
    topic: str = Field(..., min_length=10, max_length=500, description="Discussion topic")
    num_roles: int = Field(4, ge=2, le=8, description="Number of roles to create")
    model_preferences: Optional[List[str]] = Field(None, description="Preferred models for agents")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "What are the best strategies for treating chronic migraine?",
                "num_roles": 4,
                "model_preferences": ["gpt-4", "claude-3-opus"]
            }
        }


class RoleResponse(BaseModel):
    """Single role response"""
    name: str
    expertise: str
    perspective: str
    model: str
    system_prompt: str


class PreviewRolesResponse(BaseModel):
    """Response for role preview"""
    topic: str
    roles: List[RoleResponse]
    topic_analysis: Dict[str, Any]


class RoleTemplate(BaseModel):
    """Predefined role template"""
    id: str
    name: str
    expertise: str
    perspective: str
    applicable_topics: List[str]
    example_use_cases: List[str]


class AnalyzeTopicRequest(BaseModel):
    """Request to analyze a topic"""
    topic: str = Field(..., min_length=10, max_length=500, description="Topic to analyze")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "What are the implications of artificial intelligence in healthcare?"
            }
        }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/preview", response_model=PreviewRolesResponse)
async def preview_roles(request: PreviewRolesRequest):
    """
    Preview AI roles that would be created for a topic

    This endpoint analyzes the topic and generates appropriate expert roles
    WITHOUT starting a discussion. It's useful for:
    - Understanding what roles will be created
    - Verifying topic analysis
    - Planning discussion composition

    The actual discussion creation happens via /api/discussions/create
    """
    try:
        logger.info(f"Previewing roles for topic: {request.topic}")

        # Analyze topic first
        analysis = await role_creator.analyze_topic(request.topic)

        # Create roles
        roles = await role_creator.create_roles(
            topic=request.topic,
            num_roles=request.num_roles,
            model_preferences=request.model_preferences
        )

        # Convert to response format
        role_responses = [
            RoleResponse(
                name=role.name,
                expertise=role.expertise,
                perspective=role.perspective,
                model=role.model,
                system_prompt=role.system_prompt
            )
            for role in roles
        ]

        logger.info(f"Generated {len(roles)} roles for preview")

        return PreviewRolesResponse(
            topic=request.topic,
            roles=role_responses,
            topic_analysis={
                "domain": analysis.domain,
                "complexity": analysis.complexity,
                "key_aspects": analysis.key_aspects,
                "recommended_expertise": analysis.recommended_expertise
            }
        )

    except Exception as e:
        logger.error(f"Failed to preview roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to preview roles: {str(e)}")


@router.get("/templates", response_model=List[RoleTemplate])
async def get_role_templates():
    """
    Get predefined role templates

    Returns a list of common role archetypes that can be used across
    different discussions. These are general-purpose roles that adapt
    to specific topics.
    """
    try:
        logger.info("Fetching role templates")

        templates = [
            RoleTemplate(
                id="researcher",
                name="Research Scientist",
                expertise="Evidence-based analysis and empirical research",
                perspective="Academic rigor, peer-reviewed studies, systematic reviews",
                applicable_topics=["medical", "scientific", "technical"],
                example_use_cases=[
                    "Medical treatment discussions",
                    "Climate change debates",
                    "Technology assessments"
                ]
            ),
            RoleTemplate(
                id="practitioner",
                name="Practitioner",
                expertise="Real-world application and practical experience",
                perspective="Hands-on experience, pragmatic solutions, field expertise",
                applicable_topics=["medical", "business", "engineering"],
                example_use_cases=[
                    "Clinical medicine",
                    "Software development",
                    "Business operations"
                ]
            ),
            RoleTemplate(
                id="policy_expert",
                name="Policy Expert",
                expertise="Regulatory frameworks and policy implications",
                perspective="Legal compliance, ethical considerations, stakeholder impact",
                applicable_topics=["policy", "legal", "ethics"],
                example_use_cases=[
                    "Healthcare policy",
                    "Data privacy",
                    "Environmental regulation"
                ]
            ),
            RoleTemplate(
                id="economist",
                name="Economist",
                expertise="Economic analysis and cost-benefit evaluation",
                perspective="Financial feasibility, market dynamics, resource allocation",
                applicable_topics=["business", "policy", "healthcare"],
                example_use_cases=[
                    "Healthcare costs",
                    "Business strategy",
                    "Public policy"
                ]
            ),
            RoleTemplate(
                id="user_advocate",
                name="User/Patient Advocate",
                expertise="End-user perspective and lived experience",
                perspective="Quality of life, accessibility, user experience",
                applicable_topics=["healthcare", "product design", "social services"],
                example_use_cases=[
                    "Medical treatments",
                    "Product features",
                    "Social programs"
                ]
            ),
            RoleTemplate(
                id="systems_thinker",
                name="Systems Thinker",
                expertise="Holistic analysis and interconnected systems",
                perspective="Long-term effects, unintended consequences, systemic change",
                applicable_topics=["complex systems", "policy", "organizational"],
                example_use_cases=[
                    "Healthcare reform",
                    "Climate action",
                    "Organizational change"
                ]
            ),
            RoleTemplate(
                id="data_analyst",
                name="Data Analyst",
                expertise="Statistical analysis and data-driven insights",
                perspective="Quantitative evidence, trends, predictive models",
                applicable_topics=["business", "scientific", "technical"],
                example_use_cases=[
                    "Market analysis",
                    "Clinical trials",
                    "Performance optimization"
                ]
            ),
            RoleTemplate(
                id="ethicist",
                name="Ethicist",
                expertise="Ethical principles and moral reasoning",
                perspective="Rights, justice, fairness, ethical implications",
                applicable_topics=["medical", "policy", "AI/technology"],
                example_use_cases=[
                    "Medical ethics",
                    "AI governance",
                    "Research ethics"
                ]
            )
        ]

        logger.info(f"Returning {len(templates)} role templates")
        return templates

    except Exception as e:
        logger.error(f"Failed to get role templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=RoleTemplate)
async def get_role_template(template_id: str):
    """
    Get a specific role template by ID

    Path Parameters:
    - template_id: Template identifier (e.g., "researcher", "practitioner")

    Returns detailed information about the role template.
    """
    try:
        logger.info(f"Fetching role template: {template_id}")

        templates = await get_role_templates()
        template = next((t for t in templates if t.id == template_id), None)

        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

        return template

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-topic")
async def analyze_topic(request: AnalyzeTopicRequest):
    """
    Analyze a topic to understand domain and complexity

    Request Body:
    - topic: Discussion topic

    Returns:
    - Domain classification
    - Complexity assessment
    - Key aspects identified
    - Recommended expertise areas

    This helps understand what types of roles would be most appropriate.
    """
    try:
        logger.info(f"Analyzing topic: {request.topic}")

        analysis = await role_creator.analyze_topic(request.topic)

        return {
            "topic": request.topic,
            "domain": analysis.domain,
            "complexity": analysis.complexity,
            "key_aspects": analysis.key_aspects,
            "recommended_expertise": analysis.recommended_expertise,
            "suggested_num_roles": 4 if analysis.complexity in ["simple", "moderate"] else 6
        }

    except Exception as e:
        logger.error(f"Failed to analyze topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-domain/{domain}")
async def get_roles_by_domain(domain: str):
    """
    Get recommended role templates for a specific domain

    Path Parameters:
    - domain: Domain name (e.g., "medical", "business", "technical")

    Returns role templates that are most applicable to the specified domain.
    """
    try:
        logger.info(f"Getting roles for domain: {domain}")

        templates = await get_role_templates()

        # Filter templates by domain
        filtered_templates = [
            t for t in templates
            if domain.lower() in [topic.lower() for topic in t.applicable_topics]
        ]

        if not filtered_templates:
            logger.warning(f"No templates found for domain: {domain}")
            return {
                "domain": domain,
                "roles": [],
                "message": f"No predefined templates for domain '{domain}'. Use /preview endpoint to generate custom roles."
            }

        return {
            "domain": domain,
            "roles": filtered_templates,
            "count": len(filtered_templates)
        }

    except Exception as e:
        logger.error(f"Failed to get roles by domain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
