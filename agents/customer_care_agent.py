"""
Customer Care Agent Demo
Support agent with humility substrate
"""

from typing import Dict, Optional
import random
from .base_agent import BaseAgent, AgentCapability
from pact_ax.primitives.epistemic import EpistemicState, ConfidenceLevel
from pact_ax.coordination.humility_aware import Query
from pact_hx.expression.base import ExpressionContext, Domain, CommunicationStyle


class CustomerCareAgent(BaseAgent):
    """
    Customer care agent with explicit knowledge boundaries.
    Knows when to escalate, never hallucinates.
    """
    
    def __init__(self, agent_id: str = "care_agent_001"):
        # Define what this agent knows
        capabilities = [
            AgentCapability(
                domain="general_inquiries",
                topics=["hours", "location", "contact", "general questions"],
                proficiency_level=ConfidenceLevel.CONFIDENT,
                confidence_range=(0.8, 0.95)
            ),
            AgentCapability(
                domain="account_basics",
                topics=["login", "password reset", "account info", "profile"],
                proficiency_level=ConfidenceLevel.CONFIDENT,
                confidence_range=(0.7, 0.9)
            ),
            AgentCapability(
                domain="billing_basic",
                topics=["check balance", "payment methods", "billing cycle"],
                proficiency_level=ConfidenceLevel.MODERATE,
                confidence_range=(0.5, 0.7)
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            name="Care Agent",
            domain=Domain.CUSTOMER_CARE,
            capabilities=capabilities
        )
        
        # Set up delegation map
        self.delegation_map.add_delegation(
            "billing_complex",
            "billing_specialist",
            "Complex billing issues require specialist"
        )
        self.delegation_map.add_delegation(
            "technical",
            "technical_support",
            "Technical issues need engineering expertise"
        )
        self.delegation_map.add_delegation(
            "refunds",
            "billing_specialist",
            "Refund processing requires specialist access"
        )
        
        # Simulated knowledge base
        self.knowledge_base = {
            "hours": "We're open Monday-Friday 9am-6pm EST",
            "location": "We're headquartered in San Francisco, CA",
            "contact": "You can reach us at support@example.com or 1-800-EXAMPLE",
            "login": "To reset your password, click 'Forgot Password' on the login page",
            "password reset": "Password resets are sent to your registered email within 5 minutes",
            "account info": "You can update your account info in Settings > Profile",
            "balance": "Your current balance is shown in the Billing section of your account"
        }
    
    def _generate_answer(self, query: Query, context: ExpressionContext) -> EpistemicState:
        """
        Generate answer with appropriate confidence.
        Checks knowledge base, assesses certainty.
        """
        query_lower = query.content.lower()
        
        # Check if we have exact knowledge
        for key, value in self.knowledge_base.items():
            if key in query_lower:
                return EpistemicState(
                    value=value,
                    confidence=ConfidenceLevel.CERTAIN,
                    source="knowledge_base",
                    boundary=self.boundaries[0]
                )
        
        # Check if it's a topic we know about but don't have exact answer
        for capability in self.capabilities:
            if capability.can_handle(query.content):
                # We know about this topic but not the specific answer
                if "billing" in query_lower and "refund" in query_lower:
                    # Complex billing - low confidence
                    return EpistemicState(
                        value="I can see you're asking about refunds, but I need to connect you with our billing specialist who can process that for you.",
                        confidence=ConfidenceLevel.LOW,
                        uncertainty_reason="Refund processing requires specialist access",
                        delegation_map=self.delegation_map
                    )
                
                elif "technical" in query_lower or "error" in query_lower:
                    # Technical issue - outside domain
                    return EpistemicState(
                        value="This appears to be a technical issue",
                        confidence=ConfidenceLevel.LOW,
                        uncertainty_reason="Technical troubleshooting needs engineering team",
                        delegation_map=self.delegation_map
                    )
                
                else:
                    # General topic we handle but no specific answer
                    return EpistemicState(
                        value=f"I can help with {capability.domain} questions. Could you be more specific about what you need?",
                        confidence=ConfidenceLevel.MODERATE,
                        uncertainty_reason="Need more details to provide specific answer"
                    )
        
        # Completely outside our domain
        from pact_ax.primitives.epistemic import UnknownResponse
        return UnknownResponse(
            reason="This topic is outside my area of expertise",
            suggested_delegate="specialist_team"
        ).to_epistemic_state()
    
    def _assess_confidence(self, query: Query, capability: AgentCapability) -> ConfidenceLevel:
        """
        Assess confidence for specific query.
        More nuanced than base implementation.
        """
        query_lower = query.content.lower()
        
        # Exact match in knowledge base = high confidence
        for key in self.knowledge_base.keys():
            if key in query_lower:
                return ConfidenceLevel.CERTAIN
        
        # Topic match but no exact answer = moderate confidence
        if capability.can_handle(query.content):
            # Check for complexity indicators
            complexity_indicators = ["complex", "detailed", "specific", "technical", "refund", "cancel"]
            if any(indicator in query_lower for indicator in complexity_indicators):
                return ConfidenceLevel.LOW
            else:
                return ConfidenceLevel.MODERATE
        
        # No match = unknown
        return ConfidenceLevel.UNKNOWN


def demo_customer_care():
    """
    Demo the customer care agent.
    Show humility in action.
    """
    print("="*60)
    print("CUSTOMER CARE AGENT DEMO")
    print("Demonstrating Humility Substrate in Action")
    print("="*60)
    print()
    
    # Create agent
    agent = CustomerCareAgent()
    
    # Create context
    context = ExpressionContext(
        domain=Domain.CUSTOMER_CARE,
        style=CommunicationStyle.PROFESSIONAL,
        urgency="normal"
    )
    
    # Test queries
    test_queries = [
        ("What are your hours?", "general_inquiries", 0.6),
        ("How do I reset my password?", "account_basics", 0.6),
        ("I need a refund on my last purchase", "billing_complex", 0.7),
        ("Why is my app crashing?", "technical", 0.7),
        ("What's your company's mission?", "unknown", 0.6)
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
        print(f"  Should Escalate: {response.get('should_escalate', False)}")
        print(f"  Delegate To: {response.get('delegate_to', 'None')}")
        
        print(f"\nAGENT RESPONSE:")
        print(f"  {response['message']}")
        print()
    
    # Show stats
    print("\n" + "="*60)
    print("AGENT STATISTICS")
    print("="*60)
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()


if __name__ == "__main__":
    demo_customer_care()
