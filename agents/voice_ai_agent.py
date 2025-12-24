"""
Voice AI Assistant Demo
Conversational agent with natural humility expression
"""

from typing import Dict
from .base_agent import BaseAgent, AgentCapability
from pact_ax.primitives.epistemic import EpistemicState, ConfidenceLevel
from pact_ax.coordination.humility_aware import Query
from pact_hx.expression.base import ExpressionContext, Domain, CommunicationStyle


class VoiceAIAssistant(BaseAgent):
    """
    Voice AI assistant.
    Natural conversation with appropriate hedging.
    """
    
    def __init__(self, agent_id: str = "voice_001"):
        capabilities = [
            AgentCapability(
                domain="general_knowledge",
                topics=["facts", "definitions", "explanations", "history"],
                proficiency_level=ConfidenceLevel.CONFIDENT,
                confidence_range=(0.7, 0.9)
            ),
            AgentCapability(
                domain="current_events",
                topics=["news", "today", "recent", "latest"],
                proficiency_level=ConfidenceLevel.LOW,
                confidence_range=(0.2, 0.5)
            ),
            AgentCapability(
                domain="personal_assistant",
                topics=["reminder", "schedule", "weather", "time"],
                proficiency_level=ConfidenceLevel.CONFIDENT,
                confidence_range=(0.8, 0.95)
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            name="Voice Assistant",
            domain=Domain.VOICE_AI,
            capabilities=capabilities
        )
        
        # Delegation map
        self.delegation_map.add_delegation(
            "current_events",
            "web_search",
            "Need real-time information"
        )
        self.delegation_map.add_delegation(
            "specialized_knowledge",
            "expert_system",
            "Specialized domain needs expert"
        )
        
        # Simulated knowledge
        self.knowledge = {
            "capital": {
                "france": "Paris",
                "japan": "Tokyo",
                "usa": "Washington DC"
            },
            "definition": {
                "humility": "the quality of being humble; freedom from pride and arrogance",
                "epistemic": "relating to knowledge or to the degree of its validation"
            }
        }
    
    def _generate_answer(self, query: Query, context: ExpressionContext) -> EpistemicState:
        """Generate conversational answer"""
        query_lower = query.content.lower()
        
        # Check for current events
        current_indicators = ["today", "latest", "recent", "news", "now", "current"]
        if any(indicator in query_lower for indicator in current_indicators):
            return EpistemicState(
                value="I don't have access to real-time information",
                confidence=ConfidenceLevel.UNKNOWN,
                uncertainty_reason="No real-time data access",
                delegation_map=self.delegation_map
            )
        
        # Check knowledge base
        if "capital" in query_lower:
            for country, capital in self.knowledge["capital"].items():
                if country in query_lower:
                    return EpistemicState(
                        value=f"The capital of {country.title()} is {capital}",
                        confidence=ConfidenceLevel.CERTAIN,
                        source="knowledge_base"
                    )
        
        if "what is" in query_lower or "define" in query_lower:
            for term, definition in self.knowledge["definition"].items():
                if term in query_lower:
                    return EpistemicState(
                        value=f"{term.title()} means: {definition}",
                        confidence=ConfidenceLevel.CONFIDENT,
                        source="knowledge_base"
                    )
        
        # Weather/time queries (would integrate with APIs)
        if "weather" in query_lower:
            return EpistemicState(
                value="I can check the weather",
                confidence=ConfidenceLevel.MODERATE,
                uncertainty_reason="Would need to access weather API",
                source="capability_check"
            )
        
        # Don't know
        from pact_ax.primitives.epistemic import UnknownResponse
        return UnknownResponse(
            reason="I don't have that information",
            suggested_delegate="search" if "search" not in query_lower else None
        ).to_epistemic_state()


def demo_voice_ai():
    """
    Demo voice AI assistant.
    Show natural conversational humility.
    """
    print("="*60)
    print("VOICE AI ASSISTANT DEMO")
    print("Natural Conversational Humility")
    print("="*60)
    print()
    
    agent = VoiceAIAssistant()
    
    context = ExpressionContext(
        domain=Domain.VOICE_AI,
        style=CommunicationStyle.CONVERSATIONAL,
        urgency="normal"
    )
    
    test_queries = [
        ("What's the capital of France?", "general_knowledge", 0.7),
        ("What's the weather today?", "personal_assistant", 0.7),
        ("What happened in the news today?", "current_events", 0.7),
        ("Define epistemic for me", "general_knowledge", 0.7),
        ("Who won the election yesterday?", "current_events", 0.8)
    ]
    
    for query_text, domain, required_confidence in test_queries:
        print(f"\n{'─'*60}")
        print(f"🎤 USER: '{query_text}'")
        print(f"{'─'*60}")
        
        query = Query(
            content=query_text,
            domain=domain,
            required_confidence=required_confidence
        )
        
        response = agent.handle(query, context)
        
        print(f"\n🤖 ASSISTANT:")
        print(f"   {response['message']}")
        
        print(f"\n📊 INTERNAL STATE:")
        print(f"   Confidence: {response.get('confidence', 'N/A')}")
        print(f"   Delegate To: {response.get('delegate_to', 'None')}")
        print()
    
    # Stats
    print("\n" + "="*60)
    print("INTERACTION STATISTICS")
    print("="*60)
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()


if __name__ == "__main__":
    demo_voice_ai()
