#!/usr/bin/env python3
"""
Optimized Chunking System for Symbolic Content
Addresses chunking weaknesses with content-aware splitting and quality preservation.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class ChunkMetrics:
    """Metrics for chunk quality assessment."""
    word_count: int
    sentence_count: int
    paragraph_count: int
    symbolic_density: float
    completeness_score: float
    coherence_score: float
    optimal_size: bool


@dataclass
class OptimizedChunk:
    """Enhanced chunk with quality metrics."""
    content: str
    chunk_id: str
    source_info: Dict[str, Any]
    metrics: ChunkMetrics
    symbolic_elements: List[str]
    domain_classification: str
    processing_priority: int


class OptimizedChunkingSystem:
    """Intelligent chunking system optimized for symbolic and esoteric content."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Optimal chunk parameters for different content types
        self.chunk_parameters = {
            "symbolic_interpretation": {
                "min_words": 150,
                "max_words": 800,
                "optimal_words": 400,
                "preserve_context": True
            },
            "esoteric_text": {
                "min_words": 100,
                "max_words": 600,
                "optimal_words": 300,
                "preserve_context": True
            },
            "instructional": {
                "min_words": 200,
                "max_words": 1000,
                "optimal_words": 500,
                "preserve_context": False
            },
            "conversational": {
                "min_words": 50,
                "max_words": 400,
                "optimal_words": 200,
                "preserve_context": True
            }
        }
        
        # Symbolic content patterns for intelligent splitting
        self.symbolic_patterns = {
            "section_headers": r'^[A-Z\s\-]{3,}$|^Chapter \d+|^Book [A-Z]|^Part \d+',
            "mystical_titles": r'Adeptus|Theoricus|Practicus|Philosophus|Neophyte',
            "enumerated_items": r'^\d+\.|^[A-Z]\.|^[IVX]+\.',
            "symbolic_breaks": r'---+|===+|\*\*\*+',
            "ritual_sections": r'Opening|Closing|Invocation|Banishing|Consecration',
            "tarot_cards": r'The (Fool|Magician|High Priestess|Empress|Emperor|Hierophant|Lovers|Chariot|Strength|Hermit|Wheel|Justice|Hanged Man|Death|Temperance|Devil|Tower|Star|Moon|Sun|Judgement|World)',
            "sephiroth": r'Kether|Chokmah|Binah|Chesed|Geburah|Tiphareth|Netzach|Hod|Yesod|Malkuth'
        }
        
        # Content coherence indicators
        self.coherence_indicators = {
            "transition_words": ["however", "therefore", "furthermore", "moreover", "consequently"],
            "reference_words": ["this", "that", "these", "those", "such", "aforementioned"],
            "continuation_phrases": ["in addition", "similarly", "likewise", "on the other hand"]
        }
        
        self.logger.info("Optimized Chunking System initialized")
    
    def chunk_content(self, content: str, content_type: str = "symbolic_interpretation",
                     preserve_quality: bool = True) -> List[OptimizedChunk]:
        """Chunk content with intelligent splitting and quality preservation."""
        
        # Get parameters for content type
        params = self.chunk_parameters.get(content_type, self.chunk_parameters["symbolic_interpretation"])
        
        # Pre-process content
        processed_content = self._preprocess_content(content)
        
        # Identify natural break points
        break_points = self._identify_break_points(processed_content)
        
        # Create initial chunks
        initial_chunks = self._create_initial_chunks(processed_content, break_points, params)
        
        # Optimize chunk sizes
        optimized_chunks = self._optimize_chunk_sizes(initial_chunks, params)
        
        # Validate and enhance chunks
        final_chunks = self._validate_and_enhance_chunks(optimized_chunks, content_type)
        
        # Filter out low-quality chunks if requested
        if preserve_quality:
            final_chunks = self._filter_quality_chunks(final_chunks)
        
        self.logger.info(f"Created {len(final_chunks)} optimized chunks from {len(content)} characters")
        
        return final_chunks
    
    def _preprocess_content(self, content: str) -> str:
        """Preprocess content for optimal chunking."""
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Preserve paragraph breaks
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Clean up common formatting issues
        content = re.sub(r'([.!?])\s*([A-Z])', r'\1\n\2', content)  # Add line breaks after sentences
        content = re.sub(r'\n{3,}', '\n\n', content)  # Limit consecutive line breaks
        
        # Preserve symbolic formatting
        content = re.sub(r'(\d+\.)\s*([A-Z])', r'\1 \2', content)  # Fix numbered lists
        
        return content.strip()
    
    def _identify_break_points(self, content: str) -> List[Tuple[int, str, float]]:
        """Identify natural break points in content with quality scores."""
        
        break_points = []
        lines = content.split('\n')
        current_pos = 0
        
        for i, line in enumerate(lines):
            line_start = current_pos
            current_pos += len(line) + 1  # +1 for newline
            
            # Check for various break patterns
            for pattern_name, pattern in self.symbolic_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    quality_score = self._calculate_break_quality(line, pattern_name, i, lines)
                    break_points.append((line_start, pattern_name, quality_score))
                    break
            
            # Check for paragraph breaks
            if line.strip() == '' and i > 0 and i < len(lines) - 1:
                if lines[i-1].strip() and lines[i+1].strip():
                    quality_score = self._calculate_break_quality(line, "paragraph_break", i, lines)
                    break_points.append((line_start, "paragraph_break", quality_score))
        
        # Sort by position and filter by quality
        break_points.sort(key=lambda x: x[0])
        high_quality_breaks = [bp for bp in break_points if bp[2] > 0.6]
        
        return high_quality_breaks
    
    def _calculate_break_quality(self, line: str, pattern_type: str, line_index: int, 
                                all_lines: List[str]) -> float:
        """Calculate quality score for a potential break point."""
        
        base_scores = {
            "section_headers": 0.9,
            "mystical_titles": 0.8,
            "enumerated_items": 0.7,
            "symbolic_breaks": 0.9,
            "ritual_sections": 0.8,
            "tarot_cards": 0.7,
            "sephiroth": 0.7,
            "paragraph_break": 0.6
        }
        
        base_score = base_scores.get(pattern_type, 0.5)
        
        # Adjust based on context
        context_bonus = 0.0
        
        # Check surrounding lines for coherence
        if line_index > 0 and line_index < len(all_lines) - 1:
            prev_line = all_lines[line_index - 1].strip()
            next_line = all_lines[line_index + 1].strip()
            
            # Bonus for clear transitions
            if any(word in prev_line.lower() for word in ["therefore", "thus", "consequently"]):
                context_bonus += 0.1
            
            # Bonus for new topic indicators
            if any(word in next_line.lower() for word in ["now", "next", "furthermore", "additionally"]):
                context_bonus += 0.1
        
        return min(1.0, base_score + context_bonus)
    
    def _create_initial_chunks(self, content: str, break_points: List[Tuple[int, str, float]], 
                              params: Dict[str, Any]) -> List[str]:
        """Create initial chunks based on break points."""
        
        if not break_points:
            # No break points found, split by word count
            return self._split_by_word_count(content, params["optimal_words"])
        
        chunks = []
        start_pos = 0
        
        for break_pos, break_type, quality in break_points:
            if break_pos > start_pos:
                chunk_content = content[start_pos:break_pos].strip()
                if chunk_content:
                    chunks.append(chunk_content)
                start_pos = break_pos
        
        # Add final chunk
        if start_pos < len(content):
            final_chunk = content[start_pos:].strip()
            if final_chunk:
                chunks.append(final_chunk)
        
        return chunks
    
    def _split_by_word_count(self, content: str, target_words: int) -> List[str]:
        """Split content by word count when no natural breaks are found."""
        
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), target_words):
            chunk_words = words[i:i + target_words]
            chunks.append(' '.join(chunk_words))
        
        return chunks
    
    def _optimize_chunk_sizes(self, chunks: List[str], params: Dict[str, Any]) -> List[str]:
        """Optimize chunk sizes to meet parameters."""
        
        optimized_chunks = []
        
        for chunk in chunks:
            word_count = len(chunk.split())
            
            if word_count < params["min_words"]:
                # Chunk too small - try to merge with next
                if optimized_chunks:
                    # Merge with previous chunk
                    optimized_chunks[-1] += "\n\n" + chunk
                else:
                    # Keep as is if it's the first chunk
                    optimized_chunks.append(chunk)
            
            elif word_count > params["max_words"]:
                # Chunk too large - split it
                sub_chunks = self._split_large_chunk(chunk, params["optimal_words"])
                optimized_chunks.extend(sub_chunks)
            
            else:
                # Chunk size is good
                optimized_chunks.append(chunk)
        
        return optimized_chunks
    
    def _split_large_chunk(self, chunk: str, target_words: int) -> List[str]:
        """Split a large chunk into smaller pieces."""
        
        # Try to split at sentence boundaries first
        sentences = re.split(r'(?<=[.!?])\s+', chunk)
        
        sub_chunks = []
        current_chunk = ""
        current_words = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            if current_words + sentence_words <= target_words:
                current_chunk += sentence + " "
                current_words += sentence_words
            else:
                if current_chunk.strip():
                    sub_chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
                current_words = sentence_words
        
        if current_chunk.strip():
            sub_chunks.append(current_chunk.strip())
        
        return sub_chunks
    
    def _validate_and_enhance_chunks(self, chunks: List[str], content_type: str) -> List[OptimizedChunk]:
        """Validate chunks and create enhanced chunk objects."""
        
        enhanced_chunks = []
        
        for i, chunk_content in enumerate(chunks):
            # Calculate metrics
            metrics = self._calculate_chunk_metrics(chunk_content)
            
            # Identify symbolic elements
            symbolic_elements = self._identify_symbolic_elements(chunk_content)
            
            # Classify domain
            domain = self._classify_domain(chunk_content)
            
            # Calculate processing priority
            priority = self._calculate_processing_priority(chunk_content, metrics, symbolic_elements)
            
            # Create enhanced chunk
            enhanced_chunk = OptimizedChunk(
                content=chunk_content,
                chunk_id=f"{content_type}_{i:04d}",
                source_info={
                    "content_type": content_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "created_at": datetime.now().isoformat()
                },
                metrics=metrics,
                symbolic_elements=symbolic_elements,
                domain_classification=domain,
                processing_priority=priority
            )
            
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def _calculate_chunk_metrics(self, content: str) -> ChunkMetrics:
        """Calculate comprehensive metrics for a chunk."""
        
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        # Calculate symbolic density
        symbolic_words = ["symbol", "meaning", "represent", "divine", "sacred", "mystical", 
                         "spiritual", "archetype", "wisdom", "enlightenment", "transformation"]
        symbolic_count = sum(1 for word in words if word.lower() in symbolic_words)
        symbolic_density = symbolic_count / len(words) if words else 0
        
        # Calculate completeness score
        completeness_indicators = [
            not content.endswith('...'),
            not content.endswith('1.'),
            not re.search(r'\[.*?\]', content),
            len(sentences) > 1,
            len(words) > 50
        ]
        completeness_score = sum(completeness_indicators) / len(completeness_indicators)
        
        # Calculate coherence score
        coherence_score = self._calculate_coherence_score(content)
        
        # Determine if size is optimal
        optimal_size = 150 <= len(words) <= 800
        
        return ChunkMetrics(
            word_count=len(words),
            sentence_count=len([s for s in sentences if s.strip()]),
            paragraph_count=len([p for p in paragraphs if p.strip()]),
            symbolic_density=symbolic_density,
            completeness_score=completeness_score,
            coherence_score=coherence_score,
            optimal_size=optimal_size
        )
    
    def _calculate_coherence_score(self, content: str) -> float:
        """Calculate coherence score for content."""
        
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        
        if len(sentences) < 2:
            return 0.5
        
        coherence_score = 0.0
        total_comparisons = 0
        
        for i in range(len(sentences) - 1):
            current_words = set(sentences[i].lower().split())
            next_words = set(sentences[i + 1].lower().split())
            
            # Calculate word overlap
            overlap = len(current_words.intersection(next_words))
            total_words = len(current_words.union(next_words))
            
            if total_words > 0:
                coherence_score += overlap / total_words
                total_comparisons += 1
        
        return coherence_score / total_comparisons if total_comparisons > 0 else 0.5
    
    def _identify_symbolic_elements(self, content: str) -> List[str]:
        """Identify symbolic elements in content."""
        
        elements = []
        content_lower = content.lower()
        
        # Symbolic categories
        symbolic_categories = {
            "colors": ["red", "blue", "gold", "silver", "white", "black", "crimson", "emerald"],
            "numbers": ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "twelve"],
            "directions": ["north", "south", "east", "west", "above", "below", "center"],
            "celestial": ["sun", "moon", "star", "planet", "heaven", "sky"],
            "elements": ["fire", "water", "air", "earth", "spirit"],
            "geometric": ["circle", "triangle", "square", "cross", "pentagram", "hexagram"]
        }
        
        for category, items in symbolic_categories.items():
            found_items = [item for item in items if item in content_lower]
            if found_items:
                elements.extend([f"{category}:{item}" for item in found_items])
        
        return elements
    
    def _classify_domain(self, content: str) -> str:
        """Classify the domain of the content."""
        
        domain_keywords = {
            "tarot": ["tarot", "arcana", "card", "divination", "spread"],
            "qabalah": ["sephiroth", "tree of life", "kether", "malkuth", "path"],
            "alchemy": ["transmutation", "prima materia", "philosopher", "stone", "solve"],
            "hermetic": ["hermetic", "golden dawn", "adept", "initiation", "grade"],
            "astrology": ["planet", "zodiac", "house", "aspect", "chart"],
            "mythology": ["myth", "god", "goddess", "hero", "legend"],
            "general": []
        }
        
        content_lower = content.lower()
        domain_scores = {}
        
        for domain, keywords in domain_keywords.items():
            if domain == "general":
                continue
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        else:
            return "general"
    
    def _calculate_processing_priority(self, content: str, metrics: ChunkMetrics, 
                                     symbolic_elements: List[str]) -> int:
        """Calculate processing priority (1-10, higher is more important)."""
        
        priority = 5  # Base priority
        
        # Adjust based on symbolic density
        if metrics.symbolic_density > 0.1:
            priority += 2
        elif metrics.symbolic_density > 0.05:
            priority += 1
        
        # Adjust based on completeness
        if metrics.completeness_score > 0.8:
            priority += 1
        elif metrics.completeness_score < 0.5:
            priority -= 2
        
        # Adjust based on symbolic elements
        if len(symbolic_elements) > 5:
            priority += 1
        
        # Adjust based on size optimality
        if metrics.optimal_size:
            priority += 1
        
        return max(1, min(10, priority))
    
    def _filter_quality_chunks(self, chunks: List[OptimizedChunk]) -> List[OptimizedChunk]:
        """Filter out low-quality chunks."""
        
        quality_chunks = []
        
        for chunk in chunks:
            # Quality criteria
            quality_checks = [
                chunk.metrics.completeness_score >= 0.7,
                chunk.metrics.word_count >= 50,
                chunk.metrics.coherence_score >= 0.3,
                len(chunk.symbolic_elements) > 0 or chunk.metrics.symbolic_density > 0.02
            ]
            
            # Must pass at least 3 out of 4 quality checks
            if sum(quality_checks) >= 3:
                quality_chunks.append(chunk)
            else:
                self.logger.warning(f"Filtered out low-quality chunk: {chunk.chunk_id}")
        
        return quality_chunks
    
    def get_chunking_statistics(self, chunks: List[OptimizedChunk]) -> Dict[str, Any]:
        """Get comprehensive statistics about the chunking results."""
        
        if not chunks:
            return {"error": "No chunks to analyze"}
        
        word_counts = [chunk.metrics.word_count for chunk in chunks]
        completeness_scores = [chunk.metrics.completeness_score for chunk in chunks]
        coherence_scores = [chunk.metrics.coherence_score for chunk in chunks]
        symbolic_densities = [chunk.metrics.symbolic_density for chunk in chunks]
        
        domain_distribution = {}
        for chunk in chunks:
            domain = chunk.domain_classification
            domain_distribution[domain] = domain_distribution.get(domain, 0) + 1
        
        return {
            "total_chunks": len(chunks),
            "word_count_stats": {
                "min": min(word_counts),
                "max": max(word_counts),
                "average": sum(word_counts) / len(word_counts),
                "optimal_size_chunks": sum(1 for chunk in chunks if chunk.metrics.optimal_size)
            },
            "quality_stats": {
                "average_completeness": sum(completeness_scores) / len(completeness_scores),
                "average_coherence": sum(coherence_scores) / len(coherence_scores),
                "average_symbolic_density": sum(symbolic_densities) / len(symbolic_densities),
                "high_quality_chunks": sum(1 for chunk in chunks if chunk.metrics.completeness_score > 0.8)
            },
            "domain_distribution": domain_distribution,
            "priority_distribution": {
                f"priority_{i}": sum(1 for chunk in chunks if chunk.processing_priority == i)
                for i in range(1, 11)
            }
        }


def get_optimized_chunking_system() -> OptimizedChunkingSystem:
    """Get the optimized chunking system."""
    return OptimizedChunkingSystem()


if __name__ == "__main__":
    # Test the optimized chunking system
    chunking_system = get_optimized_chunking_system()
    
    print("📊 OPTIMIZED CHUNKING SYSTEM")
    print("=" * 50)
    
    # Test content
    test_content = """Book T - The Tarot
Comprising Manuscripts N, O, P, Q, R, and an Unlettered Theoricus
Adeptus Minor Instruction

A Description of the Cards of the Tarot with their Attributions; Including
a Method of Divination by Their Use

The Tarot is a symbolic system representing the journey of the soul through various stages of spiritual development. Each card serves as a mirror reflecting different aspects of human experience and divine wisdom.

The Major Arcana consists of 22 cards, each representing a major life lesson or spiritual principle. From The Fool's innocent beginning to The World's completion, these cards map the path of enlightenment.

The Minor Arcana, divided into four suits, represents the practical aspects of daily life infused with spiritual meaning. Wands symbolize fire and creativity, Cups represent water and emotion, Swords embody air and intellect, while Pentacles ground us in earth and material reality."""
    
    # Test chunking
    chunks = chunking_system.chunk_content(test_content, "symbolic_interpretation")
    
    print(f"Created {len(chunks)} optimized chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"  Words: {chunk.metrics.word_count}")
        print(f"  Domain: {chunk.domain_classification}")
        print(f"  Priority: {chunk.processing_priority}")
        print(f"  Completeness: {chunk.metrics.completeness_score:.2f}")
        print(f"  Symbolic Elements: {len(chunk.symbolic_elements)}")
        print(f"  Content Preview: {chunk.content[:100]}...")
    
    # Show statistics
    stats = chunking_system.get_chunking_statistics(chunks)
    print(f"\n📊 CHUNKING STATISTICS:")
    print(f"Total Chunks: {stats['total_chunks']}")
    print(f"Average Words: {stats['word_count_stats']['average']:.1f}")
    print(f"Average Quality: {stats['quality_stats']['average_completeness']:.2f}")
    print(f"Domain Distribution: {stats['domain_distribution']}")
    
    print("\n📊 Optimized chunking system ready for production use!")
