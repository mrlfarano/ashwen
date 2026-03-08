import json
from collections.abc import AsyncIterator
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Message
from app.services.llm import get_provider


class AgentBase:
    def __init__(self, agent: Agent, session: AsyncSession):
        self.agent = agent
        self.session = session
        self._llm = None

    async def get_llm(self):
        if self._llm is None:
            config = json.loads(self.agent.llm_config) if self.agent.llm_config else {}
            self._llm = await get_provider(self.agent.llm_provider, self.session, config)
        return self._llm

    async def respond(self, messages: list[dict], stream: bool = True) -> AsyncIterator[str] | str:
        llm = await self.get_llm()
        config = json.loads(self.agent.llm_config) if self.agent.llm_config else {}
        config["model"] = self.agent.llm_model
        
        if stream:
            return llm.stream(messages, self.agent.system_prompt, config)
        else:
            return await llm.complete(messages, self.agent.system_prompt, config)

    async def save_message(self, role: str, content: str, confidence: float = None, tokens: int = None):
        message = Message(
            project_id=self.agent.project_id,
            agent_id=self.agent.id,
            role=role,
            content=content,
            confidence=confidence,
            tokens_used=tokens,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def should_chime_in(self, context: dict) -> tuple[bool, float, str]:
        if not self.agent.proactivity_enabled:
            return False, 0.0, ""
        
        prompt = f"""You are analyzing a conversation in a project building session.
Your role: {self.agent.persona}
Your name: {self.agent.name}

Recent context:
{json.dumps(context, indent=2)}

Should you contribute to this conversation? Consider:
1. Is your expertise directly relevant?
2. Do you have valuable insight to add?
3. Would your input help move the project forward?

Respond with a JSON object:
{{"should_respond": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}
"""

        llm = await self.get_llm()
        config = json.loads(self.agent.llm_config) if self.agent.llm_config else {}
        config["model"] = self.agent.llm_model
        
        response = await llm.complete([{"role": "user", "content": prompt}], "", config)
        
        try:
            data = json.loads(response.strip().strip("`"))
            confidence = float(data.get("confidence", 0))
            should = data.get("should_respond", False) and confidence >= self.agent.confidence_threshold
            return should, confidence, data.get("reason", "")
        except (json.JSONDecodeError, ValueError):
            return False, 0.0, ""


async def get_agent_instance(agent_id: str, session: AsyncSession) -> Optional[AgentBase]:
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return None
    return AgentBase(agent, session)
