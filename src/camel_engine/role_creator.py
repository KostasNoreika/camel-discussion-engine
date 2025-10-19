"""
Dynamic Role Creator
Analyzes topics and creates appropriate expert roles for discussions
"""
import json
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from loguru import logger

from src.camel_engine.llm_provider import OpenRouterClient


class RoleDefinition(BaseModel):
    """Definition of an expert role in a discussion"""
    name: str = Field(..., description="Role name (e.g., 'Neurologist')")
    expertise: str = Field(..., description="Area of expertise")
    perspective: str = Field(..., description="Unique perspective this role brings")
    model: str = Field(..., description="LLM model to use (e.g., 'gpt-4')")
    system_prompt: str = Field(..., description="Tailored system prompt for this role")


class TopicAnalysis(BaseModel):
    """Analysis of a discussion topic"""
    primary_domain: str = Field(..., description="Main domain (medical, technical, etc.)")
    sub_domains: List[str] = Field(default_factory=list, description="Related sub-domains")
    complexity: int = Field(..., ge=1, le=5, description="Complexity level 1-5")
    key_aspects: List[str] = Field(default_factory=list, description="Key aspects to cover")
    recommended_expert_types: List[str] = Field(default_factory=list)


class RoleCreator:
    """
    Dynamically creates expert roles based on topic analysis

    Uses GPT-4 to:
    1. Analyze the discussion topic
    2. Generate appropriate expert roles
    3. Create tailored system prompts
    """

    def __init__(self, llm_client: OpenRouterClient, analysis_model: str = "openai/gpt-5-chat"):
        self.llm_client = llm_client
        self.analysis_model = analysis_model

    async def create_roles(
        self,
        topic: str,
        num_roles: int = 4,
        model_preferences: Optional[List[str]] = None
    ) -> List[RoleDefinition]:
        """
        Analyze topic and create appropriate expert roles

        Args:
            topic: Discussion topic
            num_roles: Number of roles to create
            model_preferences: Preferred models for roles (if any)

        Returns:
            List of role definitions
        """
        logger.info(f"Creating {num_roles} roles for topic: {topic}")

        # Step 1: Analyze the topic
        analysis = await self.analyze_topic(topic)
        logger.debug(f"Topic analysis: {analysis.primary_domain}, complexity {analysis.complexity}")

        # Step 2: Generate role definitions
        roles = await self.generate_roles(analysis, num_roles, model_preferences)

        # Step 3: Create system prompts for each role
        for role in roles:
            role.system_prompt = self.create_system_prompt(role, topic)

        logger.info(f"Created {len(roles)} roles: {[r.name for r in roles]}")
        return roles

    async def analyze_topic(self, topic: str) -> TopicAnalysis:
        """
        Analyze topic to understand domain and complexity

        Args:
            topic: Discussion topic to analyze

        Returns:
            Structured topic analysis
        """
        prompt = f"""Analyze this discussion topic and determine:
1. Primary domain (medical, technical, business, scientific, social, etc.)
2. Sub-domains involved
3. Complexity level (1-5, where 1=simple, 5=highly complex)
4. Key aspects that should be covered
5. What types of experts would be valuable

Topic: "{topic}"

Return your analysis as a JSON object with these exact keys:
- primary_domain (string)
- sub_domains (array of strings)
- complexity (number 1-5)
- key_aspects (array of strings)
- recommended_expert_types (array of strings)

Example:
{{
  "primary_domain": "medical",
  "sub_domains": ["neurology", "pharmacology", "pain_management"],
  "complexity": 4,
  "key_aspects": ["diagnosis", "treatment options", "side effects", "patient quality of life"],
  "recommended_expert_types": ["Neurologist", "Pharmacologist", "Pain Management Specialist", "Patient Advocate"]
}}
"""

        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self.llm_client.chat_completion_structured(
                model=self.analysis_model,
                messages=messages,
                temperature=0.3  # Low temperature for consistent analysis
            )

            return TopicAnalysis(**response)

        except Exception as e:
            logger.error(f"Topic analysis failed: {str(e)}")
            # Fallback to generic analysis
            return TopicAnalysis(
                primary_domain="general",
                sub_domains=[],
                complexity=3,
                key_aspects=["analysis", "discussion", "consensus"],
                recommended_expert_types=["Expert 1", "Expert 2", "Expert 3", "Expert 4"]
            )

    async def generate_roles(
        self,
        analysis: TopicAnalysis,
        num_roles: int,
        model_preferences: Optional[List[str]] = None
    ) -> List[RoleDefinition]:
        """
        Generate specific expert roles based on analysis

        Args:
            analysis: Topic analysis result
            num_roles: Number of roles to generate
            model_preferences: Preferred models to use

        Returns:
            List of role definitions (without system prompts yet)
        """
        # Default model distribution - LATEST 2025 models (CORRECT NAMES)
        # Key fix: Use gpt-5-chat (not gpt-5 which is o1-preview with reasoning mode)
        if not model_preferences:
            model_preferences = [
                "anthropic/claude-sonnet-4.5",      # Claude Sonnet 4.5 - Latest
                "openai/gpt-5-chat",                # GPT-5 Chat - Latest (no reasoning mode)
                "google/gemini-2.5-pro",            # Gemini 2.5 Pro - Latest
                "deepseek/deepseek-v3.2-exp"        # DeepSeek v3.2 Exp - Latest
            ]

        # Ensure we have enough models (cycle through latest ones)
        while len(model_preferences) < num_roles:
            model_preferences.append("anthropic/claude-sonnet-4.5")

        prompt = f"""Based on this topic analysis, create {num_roles} expert roles for a discussion.

Domain: {analysis.primary_domain}
Sub-domains: {', '.join(analysis.sub_domains)}
Complexity: {analysis.complexity}/5
Key aspects: {', '.join(analysis.key_aspects)}

For each role, provide:
- name: Role title (e.g., "Neurologist", "Cloud Architect", "Financial Analyst")
- expertise: Specific area of expertise
- perspective: Unique perspective this role brings to the discussion

Return as JSON array of objects.

Example:
[
  {{
    "name": "Neurologist",
    "expertise": "Brain disorders and nervous system treatment",
    "perspective": "Clinical diagnosis and evidence-based treatment protocols"
  }},
  {{
    "name": "Pharmacologist",
    "expertise": "Drug interactions and medication management",
    "perspective": "Pharmaceutical safety and efficacy"
  }}
]
"""

        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self.llm_client.chat_completion_structured(
                model=self.analysis_model,
                messages=messages,
                temperature=0.7  # Higher creativity for role generation
            )

            # Parse response and create RoleDefinition objects
            roles = []

            # Handle different response formats
            if isinstance(response, list):
                role_data = response
            elif isinstance(response, dict):
                # Check if it's a single role or has a 'roles' key
                if "name" in response and "expertise" in response:
                    role_data = [response]  # Single role object
                else:
                    role_data = response.get("roles", [])
            else:
                role_data = []

            for i, role_dict in enumerate(role_data[:num_roles]):
                role = RoleDefinition(
                    name=role_dict["name"],
                    expertise=role_dict["expertise"],
                    perspective=role_dict["perspective"],
                    model=model_preferences[i],
                    system_prompt=""  # Will be filled later
                )
                roles.append(role)

            # If we got fewer roles than requested, generate more
            if len(roles) < num_roles:
                logger.warning(f"LLM returned {len(roles)} roles, requested {num_roles}. Using fallback for remaining roles.")
                for i in range(len(roles), num_roles):
                    roles.append(RoleDefinition(
                        name=f"Expert {i+1}",
                        expertise=f"General expertise in {analysis.primary_domain}",
                        perspective=f"Perspective {i+1}",
                        model=model_preferences[i],
                        system_prompt=""
                    ))

            return roles

        except Exception as e:
            logger.error(f"Role generation failed: {str(e)}")
            # Fallback to generic roles
            return [
                RoleDefinition(
                    name=f"Expert {i+1}",
                    expertise=f"General expertise in {analysis.primary_domain}",
                    perspective=f"Perspective {i+1}",
                    model=model_preferences[i],
                    system_prompt=""
                )
                for i in range(num_roles)
            ]

    def create_system_prompt(self, role: RoleDefinition, topic: str) -> str:
        """
        Create tailored system prompt for each role

        Args:
            role: Role definition
            topic: Discussion topic

        Returns:
            Complete system prompt for the role
        """
        return f"""You are a {role.name} with deep expertise in {role.expertise}.

Your unique perspective: {role.perspective}

You are participating in a multi-agent discussion about: "{topic}"

Guidelines for your participation:
1. **Expertise-driven**: Contribute based on your specific knowledge and experience
2. **Respectful challenge**: When you disagree, explain why from your expertise
3. **Acknowledge others**: Recognize good points made by other participants
4. **Seek consensus**: Work toward agreement while maintaining professional standards
5. **Direct addressing**: Use @Name to address specific participants when relevant
6. **Natural conversation**: Don't use "Round X" or structured formats - just contribute naturally

Example interaction:
"@Pharmacologist, I appreciate your point about beta-blocker efficacy. However, from a neurological perspective, we must also consider the impact on cerebral blood flow..."

Remember: You are a real expert in your field. Be confident, be professional, and contribute meaningfully to reach the best solution.
"""


class RoleManager:
    """Manages role lifecycle and assignments"""

    def __init__(self):
        self.active_roles: Dict[str, RoleDefinition] = {}

    def register_role(self, discussion_id: str, role: RoleDefinition):
        """Register a role for a discussion"""
        key = f"{discussion_id}:{role.name}"
        self.active_roles[key] = role

    def get_role(self, discussion_id: str, role_name: str) -> Optional[RoleDefinition]:
        """Retrieve a role definition"""
        key = f"{discussion_id}:{role_name}"
        return self.active_roles.get(key)

    def list_roles(self, discussion_id: str) -> List[RoleDefinition]:
        """List all roles for a discussion"""
        prefix = f"{discussion_id}:"
        return [
            role for key, role in self.active_roles.items()
            if key.startswith(prefix)
        ]
