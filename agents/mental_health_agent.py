"""
Mental Health Support Agent Demo
Therapeutic support with safety-first humility
"""

from typing import Dict, Optional
from .base_agent import BaseAgent, AgentCapability
from pact_ax.primitives.epistemic import EpistemicState, ConfidenceLevel
from pact_ax.coordination.humility_aware import Query
from pact_hx.expression.base import ExpressionContext, Domain, CommunicationStyle
from pact_hx.expression.mental_health import TherapeuticSafety


class MentalHealthSupportAgent(BaseAgent):
    """
    Mental health support agent.
    HIGHEST epistemic standards - safety critical.
    """
    
    # This agent has VERY limited capabilities by design
    # It knows its boundaries and defers aggressively
    
    def __init__(self, agent_id: str = "mh_support_001"):
        capabilities = [
            AgentCapability(
                domain="general_wellness",
                topics=["stress", "sleep", "exercise", "routine", "self-care"],
                proficiency_level=ConfidenceLevel.MODERATE,
                confidence_range=(0.5, 0.7)
            ),
            AgentCapability(
                domain="coping_techniques",
                topics=["breathing", "grounding", "journaling", "mindfulness"],
                proficiency_level=ConfidenceLevel.CONFIDENT,
                confidence_range=(0.7, 0.85)
            ),
            AgentCapability(
                domain="session_continuity",
                topics=["previous session", "progress", "goals"],
                proficiency_level=ConfidenceLevel.MODERATE,
                confidence_range=(0.6, 0.8)
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            name="Mental Health Support",
            domain=Domain.MENTAL_HEALTH,
            capabilities=capabilities
        )
        
        # Set up strict delegation
        self.delegation_map.add_delegation(
            "diagnosis",
            "licensed_therapist",
            "Diagnosis requires licensed clinical expertise"
        )
        self.delegation_map.add_delegation(
            "medication",
            "psychiatrist",
            "Medication questions need psychiatric expertise"
        )
        self.delegation_map.add_delegation(
            "crisis",
            "crisis_hotline",
            "Crisis situations need immediate professional support"
        )
        self.delegation_map.add_delegation(
            "severe_symptoms",
            "licensed_therapist",
            "Severe symptoms require clinical assessment"
        )
        
        # Safety checker
        self.safety = TherapeuticSafety()
        
        # Simulated session history (normally would be persistent)
        self.session_history = {
            "stress_techniques": "We've practiced box breathing and progressive muscle relaxation",
            "goals": "Working on establishing consistent sleep routine",
            "progress": "You mentioned feeling more grounded after our breathing exercises"
        }
    
    def _generate_answer(self, query: Query, context: ExpressionContext) -> EpistemicState:
        """
        Generate answer with VERY high epistemic bar.
        When in doubt, defer to human.
        """
        query_lower = query.content.lower()
        
        # Check for crisis - IMMEDIATE override
        is_crisis, crisis_type = self.safety.check_for_crisis(query.content)
        if is_crisis:
            from pact_hx.expression.mental_health import MentalHealthExpression
            crisis_response = MentalHealthExpression().generate_crisis_response()
            return EpistemicState(
                value=crisis_response,
                confidence=ConfidenceLevel.CERTAIN,  # Certain about need to escalate
                source="crisis_protocol"
            )
        
        # Check if requires human
        from pact_hx.expression.mental_health import MentalHealthExpression
        requires_human = MentalHealthExpression().check_requires_human(query.content)
        if requires_human:
            return EpistemicState(
                value="This needs discussion with your therapist",
                confidence=ConfidenceLevel.UNKNOWN,
                uncertainty_reason="Topic requires licensed clinical expertise",
                delegation_map=self.delegation_map
            )
        
        # Check if it's about coping techniques (our strongest area)
        if any(technique in query_lower for technique in ["breathing", "grounding", "mindfulness"]):
            answer = self._get_coping_technique_guidance(query_lower)
            return EpistemicState(
                value=answer,
                confidence=ConfidenceLevel.CONFIDENT,
                source="evidence_based_techniques",
                uncertainty_reason=None
            )
        
        # Check if it's about session continuity
        if any(term in query_lower for term in ["previous", "last time", "we discussed", "progress"]):
            answer = self._recall_session_context(query_lower)
            return EpistemicState(
                value=answer,
                confidence=ConfidenceLevel.MODERATE,
                source="session_history"
            )
        
        # General wellness - lower confidence, invite collaboration
        if any(term in query_lower for term in ["stress", "sleep", "routine"]):
            answer = self._provide_general_wellness_support(query_lower)
            return EpistemicState(
                value=answer,
                confidence=ConfidenceLevel.MODERATE,
                uncertainty_reason="General guidance - your therapist can personalize this for you"
            )
        
        # Default: defer to therapist
        from pact_ax.primitives.epistemic import UnknownResponse
        return UnknownResponse(
            reason="This is outside my scope as a support tool",
            suggested_delegate="licensed_therapist"
        ).to_epistemic_state()
    
    def _get_coping_technique_guidance(self, query: str) -> str:
        """Provide evidence-based coping technique guidance"""
        if "breathing" in query:
            return "Let's try box breathing: Breathe in for 4 counts, hold for 4, out for 4, hold for 4. Repeat 4 times. This activates your parasympathetic nervous system."
        elif "grounding" in query:
            return "Try the 5-4-3-2-1 technique: Name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste. This brings you to the present moment."
        elif "mindfulness" in query:
            return "A simple mindfulness practice: Focus on your breath for 2 minutes. When your mind wanders, gently bring attention back. No judgment, just noticing."
        else:
            return "There are several evidence-based techniques we can explore. What specifically would help you right now?"
    
    def _recall_session_context(self, query: str) -> str:
        """Recall previous session context"""
        if "stress" in query:
            return self.session_history.get("stress_techniques", "We can explore stress management techniques together")
        elif "goal" in query:
            return self.session_history.get("goals", "Let's review your current goals")
        elif "progress" in query:
            return self.session_history.get("progress", "Let's reflect on your journey so far")
        else:
            return "From our previous conversations, we've been working on building coping strategies together"
    
    def _provide_general_wellness_support(self, query: str) -> str:
        """Provide general wellness support"""
        if "sleep" in query:
            return "Sleep routine is important. Some general guidance: consistent bedtime, limit screens before bed, create calming environment. Your therapist can help tailor this to your specific situation."
        elif "stress" in query:
            return "Stress management often involves multiple approaches. We can work on breathing techniques and grounding exercises. Your therapist can help identify your specific stressors."
        else:
            return "Wellness involves physical, emotional, and mental aspects. What area feels most important to focus on right now?"


def demo_mental_health():
    """
    Demo mental health support agent.
    Show safety-first humility.
    """
    print("="*60)
    print("MENTAL HEALTH SUPPORT AGENT DEMO")
    print("Safety-First Humility in Action")
    print("="*60)
    print()
    
    agent = MentalHealthSupportAgent()
    
    context = ExpressionContext(
        domain=Domain.MENTAL_HEALTH,
        style=CommunicationStyle.CLINICAL,
        urgency="normal"
    )
    
    test_queries = [
        ("Can you teach me the breathing technique we discussed?", "coping_techniques", 0.7),
        ("I'm having trouble sleeping lately", "general_wellness", 0.8),
        ("Do you think I have depression?", "diagnosis", 0.9),  # Should refuse
        ("I'm feeling really stressed about work", "general_wellness", 0.7),
        ("I'm thinking about hurting myself", "crisis", 0.9),  # Should trigger crisis response
        ("What did we talk about last session?", "session_continuity", 0.7)
    ]
    
    for query_text, domain, required_confidence in test_queries:
        print(f"\n{'─'*60}")
        print(f"USER: {query_text}")
        print(f"{'─'*60}")
        
        query = Query(
            content=query_text,
            domain=domain,
            required_confidence=required_confidence
        )
        
        response = agent.handle(query, context)
        
        print(f"\nAGENT ASSESSMENT:")
        print(f"  Domain: {domain}")
        print(f"  Confidence: {response.get('confidence', 'N/A')}")
        print(f"  Safety Override: {response.get('safety_override', False)}")
        print(f"  Should Escalate: {response.get('should_escalate', False)}")
        
        print(f"\nAGENT RESPONSE:")
        print(f"  {response['message']}")
        print()
        
        # Pause for dramatic effect on crisis
        if response.get('safety_override'):
            print("  ⚠️  CRISIS PROTOCOL ACTIVATED")
            print()
    
    # Show safety stats
    print("\n" + "="*60)
    print("SAFETY STATISTICS")
    print("="*60)
    safety_metrics = agent.safety.get_safety_metrics()
    for key, value in safety_metrics.items():
        print(f"  {key}: {value}")
    print()


if __name__ == "__main__":
    demo_mental_health()
