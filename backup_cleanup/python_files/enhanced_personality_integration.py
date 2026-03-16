#!/usr/bin/env python3
"""
Enhanced Personality Integration System
Ensures active personality is consistently applied to all GPT prompting, parsing, and processing.
"""

import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

from personality_modifier import PersonalityModifier, PersonalityResult
from custom_personality_manager import get_custom_personality_manager, CustomPersonality
from disciplined_prompting import get_disciplined_prompting_system


@dataclass
class PersonalityContext:
    """Context for personality application throughout processing."""
    personality_name: str
    personality_description: str
    strength: float
    is_custom: bool
    custom_config: Optional[Dict[str, Any]] = None
    application_history: List[str] = None
    
    def __post_init__(self):
        if self.application_history is None:
            self.application_history = []


class EnhancedPersonalityIntegration:
    """Enhanced system for consistent personality application across all processing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize personality components
        self.personality_modifier = PersonalityModifier()
        self.custom_personality_manager = get_custom_personality_manager()
        self.disciplined_prompting = get_disciplined_prompting_system()
        
        # Active personality context
        self.active_personality_context: Optional[PersonalityContext] = None
        
        # Personality application tracking
        self.application_log: List[Dict[str, Any]] = []
        
        self.logger.info("Enhanced Personality Integration System initialized")
    
    def set_active_personality(self, personality_name: str, strength: float = 0.7) -> PersonalityContext:
        """Set the active personality for all subsequent processing."""
        try:
            # Check if it's a custom personality
            custom_personality = self.custom_personality_manager.get_personality_for_processing(personality_name)
            
            if custom_personality:
                # Custom personality
                if isinstance(custom_personality, dict):
                    personality_desc = custom_personality.get("description", personality_name)
                    custom_strength = custom_personality.get("strength", strength)
                    custom_config = custom_personality
                else:
                    personality_desc = custom_personality.description if hasattr(custom_personality, 'description') else personality_name
                    custom_strength = custom_personality.strength if hasattr(custom_personality, 'strength') else strength
                    custom_config = {
                        "name": personality_name,
                        "description": personality_desc,
                        "strength": custom_strength
                    }
                
                context = PersonalityContext(
                    personality_name=personality_name,
                    personality_description=personality_desc,
                    strength=custom_strength,
                    is_custom=True,
                    custom_config=custom_config
                )
                
                self.logger.info(f"Set active custom personality: {personality_name} (strength: {custom_strength})")
                
            else:
                # Predefined personality
                personality_descriptions = {
                    "professional": "Formal, precise, and authoritative tone with complete sentences and technical accuracy",
                    "casual": "Relaxed, conversational tone with contractions and informal language",
                    "technical": "Precise terminology, detailed explanations, and analytical approach",
                    "educational": "Clear explanations, progressive structure, and encouraging tone",
                    "friendly": "Warm, helpful, and engaging style with positive language"
                }
                
                personality_desc = personality_descriptions.get(personality_name, f"Apply {personality_name} personality style")
                
                context = PersonalityContext(
                    personality_name=personality_name,
                    personality_description=personality_desc,
                    strength=strength,
                    is_custom=False
                )
                
                self.logger.info(f"Set active predefined personality: {personality_name} (strength: {strength})")
            
            self.active_personality_context = context
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to set active personality: {e}")
            # Fallback to neutral personality
            context = PersonalityContext(
                personality_name="neutral",
                personality_description="Neutral, balanced tone",
                strength=0.5,
                is_custom=False
            )
            self.active_personality_context = context
            return context
    
    def apply_personality_to_content(self, content: str, context_info: str = "") -> Dict[str, Any]:
        """Apply active personality to content with full tracking."""
        if not self.active_personality_context:
            self.logger.warning("No active personality set - using neutral")
            self.set_active_personality("neutral")
        
        start_time = time.time()
        
        try:
            # Apply personality using the personality modifier
            personality_result = self.personality_modifier.apply_personality(
                text=content,
                personality=self.active_personality_context.personality_name,
                strength=self.active_personality_context.strength
            )
            
            # Track application
            application_record = {
                "timestamp": datetime.now().isoformat(),
                "context_info": context_info,
                "personality_applied": self.active_personality_context.personality_name,
                "strength": self.active_personality_context.strength,
                "is_custom": self.active_personality_context.is_custom,
                "original_length": len(content),
                "modified_length": len(personality_result.modified_text),
                "confidence": personality_result.confidence,
                "cost": personality_result.cost,
                "tokens_used": personality_result.tokens_used,
                "processing_time": time.time() - start_time,
                "improvements": personality_result.improvements
            }
            
            self.application_log.append(application_record)
            self.active_personality_context.application_history.append(context_info)
            
            return {
                "success": True,
                "modified_content": personality_result.modified_text,
                "personality_result": personality_result,
                "application_record": application_record
            }
            
        except Exception as e:
            self.logger.error(f"Personality application failed: {e}")
            
            # Fallback to basic personality application
            fallback_content = self._apply_basic_personality_fallback(content)
            
            application_record = {
                "timestamp": datetime.now().isoformat(),
                "context_info": context_info,
                "personality_applied": self.active_personality_context.personality_name,
                "strength": self.active_personality_context.strength,
                "is_custom": self.active_personality_context.is_custom,
                "original_length": len(content),
                "modified_length": len(fallback_content),
                "confidence": 0.5,
                "cost": 0.0,
                "tokens_used": 0,
                "processing_time": time.time() - start_time,
                "improvements": [f"Used fallback due to error: {e}"],
                "error": str(e)
            }
            
            self.application_log.append(application_record)
            
            return {
                "success": False,
                "modified_content": fallback_content,
                "personality_result": None,
                "application_record": application_record,
                "error": str(e)
            }
    
    def enhance_prompt_with_personality(self, base_prompt: str, context: str = "prompt_enhancement") -> str:
        """Enhance any prompt with active personality specifications."""
        if not self.active_personality_context:
            return base_prompt
        
        personality_enhancement = f"""
PERSONALITY APPLICATION REQUIRED:
- Active Personality: {self.active_personality_context.personality_name}
- Description: {self.active_personality_context.personality_description}
- Strength: {self.active_personality_context.strength:.1f}
- Type: {'Custom' if self.active_personality_context.is_custom else 'Predefined'}

PERSONALITY INSTRUCTIONS:
1. Apply the specified personality consistently throughout your response
2. Maintain the personality strength level indicated
3. Preserve all factual information while adapting tone and style
4. Ensure the personality enhances rather than obscures the message

ORIGINAL PROMPT:
{base_prompt}

RESPOND WITH THE PERSONALITY FULLY APPLIED TO YOUR OUTPUT.
"""
        
        # Log prompt enhancement
        self.active_personality_context.application_history.append(f"prompt_enhancement: {context}")
        
        return personality_enhancement
    
    def get_personality_specifications_for_prompting(self) -> Dict[str, str]:
        """Get detailed personality specifications for use in prompting systems."""
        if not self.active_personality_context:
            return {
                "personality": "neutral",
                "personality_specifications": "Neutral, balanced tone with clear communication"
            }
        
        # Generate detailed specifications based on personality type
        if self.active_personality_context.is_custom:
            specifications = f"""Custom Personality: {self.active_personality_context.personality_name}
Description: {self.active_personality_context.personality_description}
Strength: {self.active_personality_context.strength:.1f}
Application: Apply this custom personality consistently throughout the response"""
        else:
            # Predefined personality specifications
            detailed_specs = {
                "professional": f"Formal tone, complete sentences, technical accuracy, authoritative voice (strength: {self.active_personality_context.strength:.1f})",
                "casual": f"Relaxed tone, contractions allowed, conversational style, informal language (strength: {self.active_personality_context.strength:.1f})",
                "technical": f"Precise terminology, detailed explanations, analytical approach, technical accuracy (strength: {self.active_personality_context.strength:.1f})",
                "educational": f"Clear explanations, progressive structure, encouraging tone, learning-focused (strength: {self.active_personality_context.strength:.1f})",
                "friendly": f"Warm tone, helpful approach, engaging style, positive language (strength: {self.active_personality_context.strength:.1f})"
            }
            
            specifications = detailed_specs.get(
                self.active_personality_context.personality_name,
                f"Apply {self.active_personality_context.personality_name} personality consistently (strength: {self.active_personality_context.strength:.1f})"
            )
        
        return {
            "personality": self.active_personality_context.personality_name,
            "personality_specifications": specifications
        }
    
    def _apply_basic_personality_fallback(self, content: str) -> str:
        """Apply basic personality transformation as fallback."""
        if not self.active_personality_context:
            return content
        
        personality = self.active_personality_context.personality_name.lower()
        strength = self.active_personality_context.strength
        
        modified_content = content
        
        if "casual" in personality and strength > 0.3:
            modified_content = modified_content.replace("do not", "don't").replace("cannot", "can't")
            modified_content = modified_content.replace("It is", "It's").replace("You are", "You're")
            
        elif "professional" in personality or "formal" in personality:
            modified_content = modified_content.replace("don't", "do not").replace("can't", "cannot")
            modified_content = modified_content.replace("It's", "It is").replace("You're", "You are")
            
        elif "friendly" in personality and strength > 0.5:
            if not modified_content.endswith(('!', '?', '.')):
                modified_content += "!"
            modified_content = modified_content.replace("This is", "This is really")
            
        elif "technical" in personality:
            modified_content = modified_content.replace("might", "may").replace("could", "can")
            
        elif "educational" in personality:
            modified_content = modified_content.replace("This is", "This concept is")
            modified_content = modified_content.replace("It works", "The process works")
        
        return modified_content
    
    def get_personality_application_stats(self) -> Dict[str, Any]:
        """Get statistics about personality application."""
        if not self.application_log:
            return {"total_applications": 0, "message": "No personality applications recorded"}
        
        total_applications = len(self.application_log)
        successful_applications = sum(1 for log in self.application_log if "error" not in log)
        
        # Calculate averages
        total_cost = sum(log.get("cost", 0) for log in self.application_log)
        total_tokens = sum(log.get("tokens_used", 0) for log in self.application_log)
        avg_confidence = sum(log.get("confidence", 0) for log in self.application_log) / total_applications
        avg_processing_time = sum(log.get("processing_time", 0) for log in self.application_log) / total_applications
        
        # Personality usage breakdown
        personality_usage = {}
        for log in self.application_log:
            personality = log.get("personality_applied", "unknown")
            personality_usage[personality] = personality_usage.get(personality, 0) + 1
        
        return {
            "total_applications": total_applications,
            "successful_applications": successful_applications,
            "success_rate": (successful_applications / total_applications) * 100,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_processing_time,
            "personality_usage": personality_usage,
            "active_personality": self.active_personality_context.personality_name if self.active_personality_context else None,
            "active_personality_strength": self.active_personality_context.strength if self.active_personality_context else None
        }
    
    def reset_personality_context(self):
        """Reset personality context and clear application history."""
        self.active_personality_context = None
        self.application_log.clear()
        self.logger.info("Personality context reset")


def get_enhanced_personality_integration() -> EnhancedPersonalityIntegration:
    """Get the enhanced personality integration system."""
    return EnhancedPersonalityIntegration()


if __name__ == "__main__":
    # Test the enhanced personality integration
    personality_system = get_enhanced_personality_integration()
    
    print("🎭 ENHANCED PERSONALITY INTEGRATION SYSTEM")
    print("=" * 60)
    
    # Test setting different personalities
    test_personalities = ["professional", "casual", "technical", "friendly"]
    
    for personality in test_personalities:
        context = personality_system.set_active_personality(personality, 0.7)
        print(f"✅ Set personality: {context.personality_name} (strength: {context.strength})")
        
        # Test content application
        test_content = "This is a test of the personality system functionality."
        result = personality_system.apply_personality_to_content(test_content, f"test_{personality}")
        
        if result["success"]:
            print(f"   Original: {test_content}")
            print(f"   Modified: {result['modified_content']}")
            print(f"   Confidence: {result['personality_result'].confidence:.2f}")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        print()
    
    # Show statistics
    stats = personality_system.get_personality_application_stats()
    print("📊 PERSONALITY APPLICATION STATISTICS:")
    print(f"Total Applications: {stats['total_applications']}")
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Average Confidence: {stats['average_confidence']:.2f}")
    print(f"Personality Usage: {stats['personality_usage']}")
    
    print("\n🎯 Enhanced personality integration system ready for production use!")
