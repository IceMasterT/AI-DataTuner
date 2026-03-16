#!/usr/bin/env python3
"""
Enhanced Symbolic Processing System
Addresses weaknesses: placeholders, incomplete entries, personality integration, chunking optimization.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

from ten_pillars_integration import get_ten_pillars_system
from enhanced_personality_integration import get_enhanced_personality_integration


@dataclass
class SymbolicContent:
    """Enhanced symbolic content structure."""
    original_text: str
    symbolic_interpretation: str
    domain: str
    complexity_level: str
    personality_applied: str
    quality_score: float
    completeness_score: float
    diversity_metrics: Dict[str, float]


class EnhancedSymbolicProcessor:
    """Enhanced processor for symbolic interpretation with quality fixes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize systems
        self.ten_pillars = get_ten_pillars_system()
        self.personality_system = get_enhanced_personality_integration()
        
        # Quality thresholds
        self.min_interpretation_length = 200
        self.min_completeness_score = 0.9
        self.min_diversity_score = 0.7
        
        # Symbolic domains for diversity
        self.symbolic_domains = {
            "hermetic": ["Golden Dawn", "Qabalah", "Tree of Life", "Sephiroth", "Hermetic"],
            "tarot": ["Major Arcana", "Minor Arcana", "divination", "archetypal"],
            "alchemical": ["transmutation", "prima materia", "philosopher's stone", "solve et coagula"],
            "mythological": ["archetype", "hero's journey", "divine", "sacred"],
            "jungian": ["collective unconscious", "shadow", "anima", "individuation"],
            "esoteric": ["initiation", "mystery", "occult", "gnosis", "enlightenment"]
        }
        
        # Personality-specific interpretation styles
        self.personality_styles = {
            "professional": {
                "tone": "scholarly and authoritative",
                "structure": "systematic analysis with clear points",
                "language": "formal academic terminology"
            },
            "casual": {
                "tone": "conversational and accessible",
                "structure": "flowing narrative with personal insights",
                "language": "everyday language with metaphors"
            },
            "technical": {
                "tone": "precise and analytical",
                "structure": "detailed breakdown with technical terms",
                "language": "specialized esoteric vocabulary"
            },
            "educational": {
                "tone": "clear and instructive",
                "structure": "progressive explanation building concepts",
                "language": "explanatory with context provided"
            },
            "friendly": {
                "tone": "warm and engaging",
                "structure": "inviting exploration with encouragement",
                "language": "approachable with enthusiasm"
            }
        }
        
        self.logger.info("Enhanced Symbolic Processor initialized")
    
    def process_symbolic_content(self, content: str, personality: str = "professional", 
                                target_format: str = "qwen") -> Dict[str, Any]:
        """Process symbolic content with enhanced quality controls."""
        
        # Set active personality
        self.personality_system.set_active_personality(personality, strength=0.8)
        
        # Analyze content for symbolic elements
        analysis = self._analyze_symbolic_content(content)
        
        # Generate high-quality interpretation
        interpretation_result = self._generate_symbolic_interpretation(
            content, personality, analysis
        )
        
        # Validate quality and completeness
        quality_result = self._validate_interpretation_quality(
            content, interpretation_result["interpretation"], personality
        )
        
        # Format for target conversation format
        formatted_result = self._format_for_conversation(
            content, interpretation_result["interpretation"], 
            target_format, personality
        )
        
        # Process through Ten Pillars for final validation
        pillars_result = self.ten_pillars.process_item(
            item_id=f"symbolic_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            content=formatted_result["conversation"],
            format_type=target_format,
            personality=personality,
            original_content=content
        )
        
        return {
            "success": pillars_result.success,
            "original_content": content,
            "symbolic_interpretation": interpretation_result["interpretation"],
            "formatted_conversation": formatted_result["conversation"],
            "personality_applied": personality,
            "quality_metrics": quality_result,
            "analysis": analysis,
            "pillars_result": pillars_result,
            "processing_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_symbolic_content(self, content: str) -> Dict[str, Any]:
        """Analyze content for symbolic elements and domain classification."""
        
        analysis = {
            "domains": [],
            "complexity_indicators": [],
            "symbolic_elements": [],
            "length": len(content),
            "word_count": len(content.split()),
            "sentence_count": len(re.split(r'[.!?]+', content))
        }
        
        content_lower = content.lower()
        
        # Domain classification
        for domain, keywords in self.symbolic_domains.items():
            matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
            if matches > 0:
                analysis["domains"].append({
                    "domain": domain,
                    "match_count": matches,
                    "relevance": matches / len(keywords)
                })
        
        # Complexity indicators
        complexity_patterns = {
            "archaic_language": r'\b(thou|thee|thy|hath|doth|unto|whereof)\b',
            "esoteric_terms": r'\b(gnosis|initiation|adept|mystery|occult|hermetic)\b',
            "symbolic_numbers": r'\b(seven|three|four|twelve|twenty-two)\b',
            "mystical_concepts": r'\b(divine|sacred|holy|eternal|infinite|transcendent)\b'
        }
        
        for indicator, pattern in complexity_patterns.items():
            matches = len(re.findall(pattern, content_lower))
            if matches > 0:
                analysis["complexity_indicators"].append({
                    "type": indicator,
                    "count": matches
                })
        
        # Symbolic elements detection
        symbolic_patterns = {
            "colors": r'\b(crimson|golden|silver|white|black|purple|emerald)\b',
            "directions": r'\b(east|west|north|south|above|below|center)\b',
            "celestial": r'\b(star|moon|sun|planet|constellation|heaven)\b',
            "geometric": r'\b(circle|triangle|square|cross|pentagram|hexagram)\b'
        }
        
        for element_type, pattern in symbolic_patterns.items():
            matches = re.findall(pattern, content_lower)
            if matches:
                analysis["symbolic_elements"].append({
                    "type": element_type,
                    "elements": list(set(matches))
                })
        
        return analysis
    
    def _generate_symbolic_interpretation(self, content: str, personality: str, 
                                        analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-quality symbolic interpretation based on analysis."""
        
        # Get personality style specifications
        style_spec = self.personality_styles.get(personality, self.personality_styles["professional"])
        
        # Build interpretation prompt based on analysis
        interpretation_prompt = self._build_interpretation_prompt(content, personality, analysis, style_spec)
        
        # Apply personality to generate interpretation
        personality_result = self.personality_system.apply_personality_to_content(
            interpretation_prompt, 
            context_info=f"symbolic_interpretation_{personality}"
        )
        
        if personality_result["success"]:
            interpretation = self._extract_interpretation_from_response(
                personality_result["modified_content"]
            )
        else:
            # Fallback to template-based interpretation
            interpretation = self._generate_fallback_interpretation(content, personality, analysis)
        
        return {
            "interpretation": interpretation,
            "personality_result": personality_result,
            "prompt_used": interpretation_prompt
        }
    
    def _build_interpretation_prompt(self, content: str, personality: str, 
                                   analysis: Dict[str, Any], style_spec: Dict[str, str]) -> str:
        """Build a comprehensive interpretation prompt."""
        
        domains_text = ", ".join([d["domain"] for d in analysis["domains"]]) if analysis["domains"] else "general symbolic"
        
        prompt = f"""SYMBOLIC INTERPRETATION TASK - {personality.upper()} PERSONALITY

CONTENT TO INTERPRET:
{content}

ANALYSIS CONTEXT:
- Symbolic Domains: {domains_text}
- Complexity Level: {"High" if len(analysis["complexity_indicators"]) > 2 else "Medium"}
- Word Count: {analysis["word_count"]}
- Symbolic Elements: {len(analysis["symbolic_elements"])} types detected

PERSONALITY REQUIREMENTS:
- Tone: {style_spec["tone"]}
- Structure: {style_spec["structure"]}
- Language: {style_spec["language"]}

INTERPRETATION GUIDELINES:
1. Provide rich, detailed symbolic analysis (minimum 200 words)
2. Connect symbols to their deeper meanings and traditions
3. Explain esoteric or mystical significance where relevant
4. Use the specified personality tone and structure consistently
5. Include specific symbolic elements and their interpretations
6. Avoid placeholders - provide complete, substantive analysis
7. Connect to broader spiritual or philosophical contexts

RESPOND WITH A COMPLETE SYMBOLIC INTERPRETATION:"""
        
        return prompt
    
    def _extract_interpretation_from_response(self, response: str) -> str:
        """Extract the actual interpretation from AI response."""
        
        # Remove common AI response prefixes
        response = re.sub(r'^(Here is|This is|The interpretation is:?)\s*', '', response, flags=re.IGNORECASE)
        
        # Remove placeholder patterns
        response = re.sub(r'\[.*?\]', '', response)
        response = re.sub(r'<.*?>', '', response)
        
        # Clean up formatting
        response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)
        response = response.strip()
        
        return response
    
    def _generate_fallback_interpretation(self, content: str, personality: str, 
                                        analysis: Dict[str, Any]) -> str:
        """Generate fallback interpretation using templates."""
        
        # Template-based interpretation for different domains
        if analysis["domains"]:
            primary_domain = analysis["domains"][0]["domain"]
            
            domain_templates = {
                "hermetic": "This passage reflects Hermetic principles of correspondence and transformation. The symbolic elements suggest a connection to the Tree of Life and the process of spiritual ascension through knowledge and practice.",
                
                "tarot": "This text embodies the archetypal wisdom of the Tarot, where each symbol represents a stage in the soul's journey. The imagery connects to the Major Arcana's themes of spiritual evolution and divine revelation.",
                
                "alchemical": "The symbolic language here mirrors alchemical processes of transformation, where base materials (consciousness) are refined into gold (enlightenment) through careful application of spiritual principles.",
                
                "mythological": "This passage draws upon universal mythological themes, where symbols serve as bridges between the conscious and unconscious mind, revealing timeless truths about human experience and divine connection.",
                
                "jungian": "From a depth psychology perspective, these symbols represent archetypal forces within the collective unconscious, offering insights into the individuation process and the integration of shadow and light.",
                
                "esoteric": "This text contains layers of esoteric meaning, where surface symbols point to deeper spiritual truths accessible only through initiation, contemplation, and inner transformation."
            }
            
            base_interpretation = domain_templates.get(primary_domain, 
                "This passage contains rich symbolic content that invites deeper contemplation and interpretation.")
        else:
            base_interpretation = "This text presents symbolic elements that resonate with universal themes of transformation, wisdom, and spiritual insight."
        
        # Expand based on detected elements
        if analysis["symbolic_elements"]:
            element_interpretations = []
            for element_group in analysis["symbolic_elements"]:
                element_type = element_group["type"]
                elements = element_group["elements"]
                
                if element_type == "colors":
                    element_interpretations.append(f"The color symbolism ({', '.join(elements)}) adds layers of meaning related to spiritual states and energetic qualities.")
                elif element_type == "directions":
                    element_interpretations.append(f"Directional references ({', '.join(elements)}) suggest cosmic orientation and the mapping of sacred space.")
                elif element_type == "celestial":
                    element_interpretations.append(f"Celestial imagery ({', '.join(elements)}) connects earthly experience to cosmic principles and divine influence.")
                elif element_type == "geometric":
                    element_interpretations.append(f"Geometric symbols ({', '.join(elements)}) represent perfect forms and mathematical harmony underlying creation.")
            
            if element_interpretations:
                base_interpretation += "\n\n" + " ".join(element_interpretations)
        
        # Apply personality-specific modifications
        if personality == "casual":
            base_interpretation = base_interpretation.replace("This passage", "This piece")
            base_interpretation = base_interpretation.replace("represents", "shows us")
        elif personality == "technical":
            base_interpretation = base_interpretation.replace("spiritual", "metaphysical")
            base_interpretation = base_interpretation.replace("divine", "transcendent")
        elif personality == "friendly":
            base_interpretation = base_interpretation.replace("This passage", "What's fascinating about this passage is that it")
            base_interpretation += "\n\nIt's really quite beautiful how these symbols work together to create such rich meaning!"
        
        return base_interpretation
    
    def _validate_interpretation_quality(self, original: str, interpretation: str, 
                                       personality: str) -> Dict[str, Any]:
        """Validate the quality of the generated interpretation."""
        
        quality_metrics = {
            "length_adequate": len(interpretation) >= self.min_interpretation_length,
            "no_placeholders": not bool(re.search(r'\[.*?\]|<.*?>|\{.*?\}', interpretation)),
            "complete_sentences": not interpretation.endswith(('...', '1.', '2.', 'etc.')),
            "personality_consistent": self._check_personality_consistency(interpretation, personality),
            "symbolic_depth": self._assess_symbolic_depth(interpretation),
            "overall_score": 0.0
        }
        
        # Calculate overall score
        score_weights = {
            "length_adequate": 0.2,
            "no_placeholders": 0.3,
            "complete_sentences": 0.2,
            "personality_consistent": 0.15,
            "symbolic_depth": 0.15
        }
        
        quality_metrics["overall_score"] = sum(
            quality_metrics[metric] * weight 
            for metric, weight in score_weights.items()
        )
        
        quality_metrics["passes_quality_check"] = quality_metrics["overall_score"] >= 0.8
        
        return quality_metrics
    
    def _check_personality_consistency(self, interpretation: str, personality: str) -> float:
        """Check if interpretation matches personality requirements."""
        
        personality_indicators = {
            "professional": ["analysis", "systematic", "framework", "principle"],
            "casual": ["really", "quite", "pretty", "kind of"],
            "technical": ["precise", "specific", "detailed", "methodology"],
            "educational": ["understand", "learn", "concept", "example"],
            "friendly": ["beautiful", "wonderful", "fascinating", "amazing"]
        }
        
        indicators = personality_indicators.get(personality, [])
        if not indicators:
            return 0.5
        
        found_indicators = sum(1 for indicator in indicators if indicator in interpretation.lower())
        return min(1.0, found_indicators / len(indicators))
    
    def _assess_symbolic_depth(self, interpretation: str) -> float:
        """Assess the depth of symbolic analysis."""
        
        depth_indicators = [
            "symbol", "represent", "meaning", "significance", "archetype",
            "tradition", "spiritual", "mystical", "esoteric", "divine",
            "transformation", "journey", "wisdom", "enlightenment", "consciousness"
        ]
        
        found_indicators = sum(1 for indicator in depth_indicators if indicator in interpretation.lower())
        return min(1.0, found_indicators / 10)  # Normalize to 0-1
    
    def _format_for_conversation(self, original: str, interpretation: str, 
                                target_format: str, personality: str) -> Dict[str, Any]:
        """Format the content for conversation training format."""
        
        if target_format == "qwen":
            conversation = f"""<|user|>
Interpret the symbolic meaning of the following passage:

{original}
<|assistant|>
{interpretation}"""
        
        elif target_format == "alpaca":
            conversation = f"""### Instruction:
Interpret the symbolic meaning of the following passage:

{original}

### Response:
{interpretation}"""
        
        elif target_format == "chatml":
            conversation = f"""<|im_start|>user
Interpret the symbolic meaning of the following passage:

{original}
<|im_end|>
<|im_start|>assistant
{interpretation}
<|im_end|>"""
        
        elif target_format == "sharegpt":
            conversation_data = {
                "conversations": [
                    {
                        "role": "user",
                        "content": f"Interpret the symbolic meaning of the following passage:\n\n{original}"
                    },
                    {
                        "role": "assistant", 
                        "content": interpretation
                    }
                ]
            }
            conversation = json.dumps(conversation_data, indent=2)
        
        else:
            # Default format
            conversation = f"User: Interpret the symbolic meaning of the following passage:\n\n{original}\n\nAssistant: {interpretation}"
        
        return {
            "conversation": conversation,
            "format": target_format,
            "personality_applied": personality
        }


def get_enhanced_symbolic_processor() -> EnhancedSymbolicProcessor:
    """Get the enhanced symbolic processor."""
    return EnhancedSymbolicProcessor()


if __name__ == "__main__":
    # Test the enhanced symbolic processor
    processor = get_enhanced_symbolic_processor()
    
    print("🔮 ENHANCED SYMBOLIC PROCESSING SYSTEM")
    print("=" * 60)
    
    # Test content with known issues
    test_content = """Book T - The Tarot
Comprising Manuscripts N, O, P, Q, R, and an Unlettered Theoricus
Adeptus Minor Instruction
A Description of the Cards of the Tarot with their Attributions; Including
a Method of Divination by Their Use
H R U"""
    
    # Test different personalities
    personalities = ["professional", "casual", "technical", "friendly"]
    
    for personality in personalities:
        print(f"\n🎭 Testing {personality} personality:")
        
        result = processor.process_symbolic_content(
            test_content, 
            personality=personality,
            target_format="qwen"
        )
        
        if result["success"]:
            print(f"   ✅ SUCCESS")
            print(f"   📊 Quality Score: {result['quality_metrics']['overall_score']:.2f}")
            print(f"   📝 Interpretation Length: {len(result['symbolic_interpretation'])} chars")
            print(f"   🎯 No Placeholders: {result['quality_metrics']['no_placeholders']}")
            print(f"   ✨ Complete: {result['quality_metrics']['complete_sentences']}")
        else:
            print(f"   ❌ FAILED")
    
    print("\n🔮 Enhanced symbolic processing system ready for production use!")
