"""
Master Demo Runner
Run all demos in sequence to show complete system
"""

import sys
from agents.customer_care_agent import demo_customer_care
from agents.mental_health_agent import demo_mental_health
from agents.voice_ai_agent import demo_voice_ai
from multi_agent_demo import demo_coordination


def main():
    """Run all demos"""
    print("\n")
    print("█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  NEUROBLOOM + PACT DEMONSTRATION".center(68) + "█")
    print("█" + "  Humility Substrate in Action".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    print("\n")
    
    demos = [
        ("Customer Care Agent", demo_customer_care),
        ("Mental Health Support Agent", demo_mental_health),
        ("Voice AI Assistant", demo_voice_ai),
        ("Multi-Agent Coordination", demo_coordination)
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n{'█'*70}")
        print(f"█ DEMO {i}/{len(demos)}: {name}")
        print(f"{'█'*70}\n")
        
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback
            traceback.print_exc()
        
        if i < len(demos):
            input("\n⏎ Press Enter to continue to next demo...")
    
    # Final summary
    print("\n")
    print("█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  DEMONSTRATION COMPLETE".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█" + "  What you just saw:".center(68) + "█")
    print("█" + "    • Agents that know their limitations".center(68) + "█")
    print("█" + "    • Confidence expressed naturally".center(68) + "█")
    print("█" + "    • Safety-first mental health handling".center(68) + "█")
    print("█" + "    • Delegation based on epistemic honesty".center(68) + "█")
    print("█" + "    • Humility as substrate, not feature".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    print("\n")


if __name__ == "__main__":
    main()
