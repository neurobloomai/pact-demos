"""
Base Agent Framework
All demo agents inherit humility substrate through this base
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import sys
sys.path.append('../..')

from pact_ax.primitives.epistemic import (
    EpistemicState,
    ConfidenceLevel,
    KnowledgeBoundary,
    DelegationMap,
    UnknownResponse
)
from pact_ax.coordination.humility_aware import Query
from pact_hx.expression.base import ExpressionContext, Domain, CommunicationStyle
from pact_hx.expression.orchestrator import ExpressionOrchestrator


@dataclass
class AgentCapability:
    """
    What an agent knows it can/cannot do.
    Explicit capability boundaries.
    """
    domain: str
    topics: List[str]
    proficiency_level: ConfidenceLevel
    confidence_range: tuple[float, float]  # (min, max) confidence for this domain
    
    def can_handle(self, topic: str) -> bool:
        """Check if topic is within capability"""
        return any(topic.lower() in t.lower() for t in self.topics)


class BaseAgent:
    """
    Base agent with humility substrate.
    All agents inherit epistemic honesty.
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        domain: Domain,
        capabilities: List[AgentCapability]
    ):
        self.id = agent_id
        self.name = name
        self.domain = domain
        self.capabilities = capabilities
        
        # Build knowledge boundaries from capabilities
        self.boundaries = self._build_boundaries()
        
        # Build delegation map
        self.delegation_map = DelegationMap()
        
        # Expression orchestrator
        self.expression = ExpressionOrchestrator()
        
        # Interaction history
        self.interaction_history: List[Dict] = []
        
        # Learning tracker
        self.learning_log: List[Dict] = []
    
    def _build_boundaries(self) -> List[KnowledgeBoundary]:
        """Build knowledge boundaries from capabilities"""
        boundaries = []
        
        for capability in self.capabilities:
            boundary = KnowledgeBoundary(
                domain=capability.domain,
                proficiency=capability.proficiency_level,
                known_capabilities=set(capability.topics),
                known_limits=set()  # Will learn these over time
            )
            boundaries.append(boundary)
        
        return boundaries
    
    def assess_capability(self, query: Query) -> EpistemicState:
        """
        Assess if agent can handle query.
        Core humility check - BEFORE attempting to answer.
        """
        # Find relevant capability
        relevant_capability = None
        for cap in self.capabilities:
            if cap.domain == query.domain or cap.can_handle(query.content):
                relevant_capability = cap
                break
        
        if not relevant_capability:
            # Outside all capabilities
            return UnknownResponse(
                reason=f"Topic '{query.domain}' is outside my expertise areas",
                suggested_delegate=self._suggest_delegate(query),
                can_learn=False
            ).to_epistemic_state()
        
        # Assess confidence for this topic
        confidence = self._assess_confidence(query, relevant_capability)
        
        # Check if should defer
        should_defer = confidence.value < query.required_confidence
        
        if should_defer:
            return EpistemicState(
                value=None,
                confidence=confidence,
                uncertainty_reason=f"My confidence ({confidence.value:.2f}) is below required threshold ({query.required_confidence})",
                boundary=self.boundaries[0],  # Primary boundary
                delegation_map=self.delegation_map
            )
        
        # Can handle
        return EpistemicState(
            value="can_handle",
            confidence=confidence,
            boundary=self.boundaries[0]
        )
    
    def _assess_confidence(self, query: Query, capability: AgentCapability) -> ConfidenceLevel:
        """
        Assess confidence for specific query.
        Subclasses override with domain-specific logic.
        """
        # Base implementation: use capability proficiency
        return capability.proficiency_level
    
    def _suggest_delegate(self, query: Query) -> Optional[str]:
        """Suggest who might handle this better"""
        return self.delegation_map.get_delegate(query.domain)
    
    def handle(self, query: Query, context: ExpressionContext) -> Dict[str, Any]:
        """
        Main entry point for handling queries.
        Assess → Answer → Express
        """
        # Step 1: Assess capability
        capability_assessment = self.assess_capability(query)
        
        # Step 2: If should defer, do so immediately
        if capability_assessment.should_defer(query.domain, query.required_confidence):
            delegate_to = capability_assessment.get_delegate(query.domain)
            response = self.expression.express(
                capability_assessment,
                context,
                query.content,
                delegate_to
            )
            
            self._log_interaction(query, capability_assessment, response, deferred=True)
            return response
        
        # Step 3: Attempt to answer
        answer_state = self._generate_answer(query, context)
        
        # Step 4: Express appropriately
        response = self.expression.express(
            answer_state,
            context,
            query.content
        )
        
        # Step 5: Log interaction
        self._log_interaction(query, answer_state, response, deferred=False)
        
        return response
    
    def _generate_answer(self, query: Query, context: ExpressionContext) -> EpistemicState:
        """
        Generate answer to query.
        Subclasses MUST override with domain logic.
        """
        raise NotImplementedError("Subclasses must implement _generate_answer")
    
    def _log_interaction(
        self,
        query: Query,
        state: EpistemicState,
        response: Dict,
        deferred: bool
    ):
        """Log interaction for learning and analytics"""
        self.interaction_history.append({
            'timestamp': datetime.now(),
            'query': query.content,
            'domain': query.domain,
            'confidence': state.confidence.value,
            'deferred': deferred,
            'response_message': response.get('message'),
            'should_escalate': response.get('should_escalate', False)
        })
    
    def learn_from_outcome(
        self,
        query: Query,
        predicted_state: EpistemicState,
        actual_outcome: bool,
        feedback: Optional[str] = None
    ):
        """
        Learn from interaction outcomes.
        Adjust confidence, update boundaries.
        """
        # Log learning event
        self.learning_log.append({
            'timestamp': datetime.now(),
            'query': query.content,
            'predicted_confidence': predicted_state.confidence.value,
            'actual_outcome': actual_outcome,
            'feedback': feedback
        })
        
        # Update boundaries if learned new limit
        if not actual_outcome and predicted_state.confidence.value > 0.6:
            # Was overconfident - add to known limits
            for boundary in self.boundaries:
                if boundary.domain == query.domain:
                    boundary.update_boundary(learned_limit=query.content)
        
        # If learned new capability
        if actual_outcome and predicted_state.confidence.value < 0.5:
            # Was underconfident - add to capabilities
            for boundary in self.boundaries:
                if boundary.domain == query.domain:
                    boundary.update_boundary(learned_capability=query.content)
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        if not self.interaction_history:
            return {"message": "No interactions yet"}
        
        total = len(self.interaction_history)
        deferred = sum(1 for i in self.interaction_history if i['deferred'])
        escalated = sum(1 for i in self.interaction_history if i.get('should_escalate'))
        avg_confidence = sum(i['confidence'] for i in self.interaction_history) / total
        
        return {
            'agent_id': self.id,
            'total_interactions': total,
            'deferred_count': deferred,
            'deferred_rate': deferred / total,
            'escalated_count': escalated,
            'avg_confidence': avg_confidence,
            'learning_events': len(self.learning_log)
        }
