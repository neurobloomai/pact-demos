"""
Multi-Agent Coordination Demo
Show agents coordinating with humility substrate
"""

import sys
sys.path.append('..')

from agents.customer_care_agent import CustomerCareAgent
from agents.mental_health_agent import MentalHealthSupportAgent
from agents.voice_ai_agent import VoiceAIAssistant

from pact_ax.coordination.humility_aware import HumilityAwareCoordinator, Query, Agent
from pact_ax.coordination.trust_primitives import TrustNetwork
from pact_hx.expression.base import ExpressionContext, Domain, CommunicationStyle


def demo_coordination():
    """
    Demo multiple agents coordinating.
    Show delegation based on epistemic honesty.
    """
    print("="*70)
    print("MULTI-AGENT COORDINATION DEMO")
    print("Humility-Based Delegation in Action")
    print("="*70)
    print()
    
    # Create agents
    care_agent = CustomerCareAgent("care_001")
    mh_agent = MentalHealthSupportAgent("mh_001")
    voice_agent = VoiceAIAssistant("voice_001")
    
    # Create coordinator
    agents = {
        "care_001": care_agent,
        "mh_001": mh_agent,
        "voice_001": voice_agent
    }
    coordinator = HumilityAwareCoordinator(agents)
    
    # Create trust network
    trust_network = TrustNetwork()
    
    # Test queries that require coordination
    test_scenarios = [
        {
            "query": "I'm feeling stressed about my bill",
            "description": "Needs both billing (care) and stress support (mental health)",
            "domain": "mixed"
        },
        {
            "query": "What are your hours?",
            "description": "Simple customer care query",
            "domain": "general_inquiries"
        },
        {
            "query": "Can you remind me about my breathing exercises?",
            "description": "Mental health continuity",
            "domain": "coping_techniques"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*70}")
        print(f"SCENARIO {i}: {scenario['description']}")
        print(f"{'='*70}")
        print(f"\nUSER: {scenario['query']}")
        print()
        
        query = Query(
            content=scenario['query'],
            domain=scenario['domain'],
            required_confidence=0.7
        )
        
        # Coordinator routes to best agent
        print("🔄 COORDINATOR: Assessing agent capabilities...")
        print()
        
        best_agent = coordinator.route_query(query)
        
        if best_agent:
            print(f"✅ ROUTED TO: {best_agent.name} ({best_agent.id})")
            print()
            
            # Agent handles query
            context = ExpressionContext(
                domain=best_agent.domain,
                style=CommunicationStyle.CONVERSATIONAL,
                urgency="normal"
            )
            
            response = best_agent.handle(query, context)
            
            print(f"🤖 {best_agent.name.upper()} RESPONSE:")
            print(f"   {response['message']}")
            print()
            
            print(f"📊 EPISTEMIC STATE:")
            print(f"   Confidence: {response.get('confidence', 'N/A'):.2f}")
            print(f"   Should Escalate: {response.get('should_escalate', False)}")
            if response.get('delegate_to'):
                print(f"   Delegate To: {response['delegate_to']}")
        else:
            print("❌ NO SUITABLE AGENT FOUND")
            print("   System would escalate to human")
        
        print()
    
    # Show coordination metrics
    print("\n" + "="*70)
    print("COORDINATION METRICS")
    print("="*70)
    
    for agent_id, agent in agents.items():
        stats = agent.get_stats()
        print(f"\n{agent.name} ({agent_id}):")
        print(f"  Interactions: {stats.get('total_interactions', 0)}")
        print(f"  Avg Confidence: {stats.get('avg_confidence', 0):.2f}")
        print(f"  Deferred Rate: {stats.get('deferred_rate', 0):.1%}")
    
    print()


if __name__ == "__main__":
    demo_coordination()
