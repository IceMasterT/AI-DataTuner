"""
Advanced chunking strategies for different content types.
Implements various methods to divide text into meaningful Q&A segments.
"""

import re
from typing import List, Tuple, Dict, Optional
from enum import Enum


class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    HEADING_BASED = "heading"
    PARAGRAPH_BASED = "paragraph"
    TOPIC_BASED = "topic"
    SENTENCE_BASED = "sentence"
    SEMANTIC_BASED = "semantic"
    MANUAL_MARKERS = "manual"


class ContentChunker:
    """Base class for content chunking strategies."""

    def chunk_content(self, text: str) -> List[Tuple[str, str]]:
        """
        Chunk content into (topic/question, content/answer) pairs.

        Args:
            text: Input text to chunk

        Returns:
            List of (question, answer) tuples
        """
        # Default implementation: paragraph-based chunking
        if not text or not text.strip():
            return []

        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # If no paragraph breaks, split by single newlines
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        # Create question-answer pairs
        chunks = []
        for paragraph in paragraphs:
            if len(paragraph) > 20:  # Filter out very short paragraphs
                question = f"Please explain the following information:"
                answer = paragraph
                chunks.append((question, answer))

        return chunks

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text


class HeadingBasedChunker(ContentChunker):
    """Chunks content based on headings and sections."""
    
    def __init__(self):
        # Patterns for different heading styles
        self.heading_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headings
            r'^(.+)\n[=-]{3,}$',  # Underlined headings
            r'^\d+\.\s+(.+)$',   # Numbered sections
            r'^[A-Z][A-Z\s]+$',  # ALL CAPS headings
            r'^(.+):$',          # Colon-terminated headings
        ]
    
    def chunk_content(self, text: str) -> List[Tuple[str, str]]:
        """Chunk based on headings and following content."""
        chunks = []
        lines = text.split('\n')
        current_heading = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a heading
            heading = self._extract_heading(line)
            if heading:
                # Save previous chunk if exists
                if current_heading and current_content:
                    content = ' '.join(current_content).strip()
                    if content:
                        question = self._heading_to_question(current_heading)
                        chunks.append((question, content))
                
                # Start new chunk
                current_heading = heading
                current_content = []
            else:
                # Add to current content
                if current_heading:
                    current_content.append(line)
        
        # Add final chunk
        if current_heading and current_content:
            content = ' '.join(current_content).strip()
            if content:
                question = self._heading_to_question(current_heading)
                chunks.append((question, content))
        
        return chunks
    
    def _extract_heading(self, line: str) -> Optional[str]:
        """Extract heading text from a line."""
        for pattern in self.heading_patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None
    
    def _heading_to_question(self, heading: str) -> str:
        """Convert heading to a question format."""
        heading = heading.strip()
        
        # If already a question, return as-is
        if heading.endswith('?'):
            return heading
        
        # Common question starters based on heading content
        if any(word in heading.lower() for word in ['benefit', 'advantage', 'pro']):
            return f"What are the benefits of {heading.lower()}?"
        elif any(word in heading.lower() for word in ['how', 'method', 'process', 'step']):
            return f"How does {heading.lower()} work?"
        elif any(word in heading.lower() for word in ['why', 'reason', 'cause']):
            return f"Why is {heading.lower()} important?"
        elif any(word in heading.lower() for word in ['what', 'definition', 'meaning']):
            return f"What is {heading.lower()}?"
        else:
            return f"Can you explain {heading.lower()}?"


class ParagraphBasedChunker(ContentChunker):
    """Chunks content based on paragraphs and natural breaks."""
    
    def __init__(self, min_paragraph_length: int = 50, max_paragraph_length: int = 500):
        self.min_length = min_paragraph_length
        self.max_length = max_paragraph_length
    
    def chunk_content(self, text: str) -> List[Tuple[str, str]]:
        """Chunk based on paragraph boundaries."""
        chunks = []
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if len(para) < self.min_length:
                continue
            
            # If paragraph is too long, split by sentences
            if len(para) > self.max_length:
                sentences = self._split_sentences(para)
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk + sentence) > self.max_length and current_chunk:
                        question = self._generate_question(current_chunk)
                        chunks.append((question, current_chunk.strip()))
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
                
                if current_chunk:
                    question = self._generate_question(current_chunk)
                    chunks.append((question, current_chunk.strip()))
            else:
                question = self._generate_question(para)
                chunks.append((question, para))
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _generate_question(self, content: str) -> str:
        """Generate a question based on content."""
        # Extract key topics from first sentence
        first_sentence = content.split('.')[0].strip()
        
        # Simple heuristics for question generation
        if any(word in content.lower() for word in ['define', 'definition', 'is', 'are']):
            return f"What is {self._extract_main_topic(first_sentence)}?"
        elif any(word in content.lower() for word in ['how', 'process', 'method', 'step']):
            return f"How does {self._extract_main_topic(first_sentence)} work?"
        elif any(word in content.lower() for word in ['why', 'because', 'reason']):
            return f"Why is {self._extract_main_topic(first_sentence)} important?"
        else:
            return f"Can you explain {self._extract_main_topic(first_sentence)}?"
    
    def _extract_main_topic(self, sentence: str) -> str:
        """Extract main topic from a sentence."""
        # Simple extraction - get first few meaningful words
        words = sentence.split()[:5]
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        meaningful_words = [w for w in words if w.lower() not in stop_words]
        return ' '.join(meaningful_words[:3]) if meaningful_words else sentence[:50]


class TopicBasedChunker(ContentChunker):
    """Chunks content based on topic transitions and key concepts."""
    
    def __init__(self):
        # Keywords that indicate topic transitions
        self.transition_keywords = [
            'however', 'moreover', 'furthermore', 'additionally', 'meanwhile',
            'on the other hand', 'in contrast', 'similarly', 'likewise',
            'first', 'second', 'third', 'finally', 'next', 'then'
        ]
        
        # Keywords that indicate new concepts
        self.concept_keywords = [
            'concept', 'principle', 'theory', 'method', 'approach', 'technique',
            'strategy', 'process', 'system', 'framework', 'model'
        ]
    
    def chunk_content(self, text: str) -> List[Tuple[str, str]]:
        """Chunk based on topic and concept boundaries."""
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_topic = ""
        current_content = []
        
        for sentence in sentences:
            # Check for topic transition
            if self._is_topic_transition(sentence) and current_content:
                # Save current chunk
                content = ' '.join(current_content).strip()
                if content:
                    question = self._generate_topic_question(current_topic or content)
                    chunks.append((question, content))
                
                # Start new chunk
                current_topic = self._extract_topic(sentence)
                current_content = [sentence]
            else:
                current_content.append(sentence)
                if not current_topic:
                    current_topic = self._extract_topic(sentence)
        
        # Add final chunk
        if current_content:
            content = ' '.join(current_content).strip()
            if content:
                question = self._generate_topic_question(current_topic or content)
                chunks.append((question, content))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_topic_transition(self, sentence: str) -> bool:
        """Check if sentence indicates a topic transition."""
        sentence_lower = sentence.lower()
        return any(keyword in sentence_lower for keyword in self.transition_keywords)
    
    def _extract_topic(self, sentence: str) -> str:
        """Extract topic from sentence."""
        # Look for concept keywords
        sentence_lower = sentence.lower()
        for keyword in self.concept_keywords:
            if keyword in sentence_lower:
                # Extract surrounding context
                words = sentence.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        start = max(0, i-2)
                        end = min(len(words), i+3)
                        return ' '.join(words[start:end])
        
        # Fallback: use first few words
        return ' '.join(sentence.split()[:6])
    
    def _generate_topic_question(self, topic: str) -> str:
        """Generate question based on topic."""
        topic = topic.strip()
        
        if any(word in topic.lower() for word in ['how', 'process', 'method']):
            return f"How does {topic} work?"
        elif any(word in topic.lower() for word in ['what', 'concept', 'definition']):
            return f"What is {topic}?"
        elif any(word in topic.lower() for word in ['why', 'benefit', 'advantage']):
            return f"Why is {topic} important?"
        else:
            return f"Can you explain {topic}?"


class ManualMarkerChunker(ContentChunker):
    """Chunks content based on manual markers and delimiters."""
    
    def __init__(self, question_markers: List[str] = None, answer_markers: List[str] = None):
        self.question_markers = question_markers or ['Q:', 'Question:', 'QUESTION:', '?']
        self.answer_markers = answer_markers or ['A:', 'Answer:', 'ANSWER:', 'Response:']
    
    def chunk_content(self, text: str) -> List[Tuple[str, str]]:
        """Chunk based on manual Q&A markers."""
        chunks = []
        lines = text.split('\n')
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for question markers
            question = self._extract_marked_content(line, self.question_markers)
            if question:
                # Save previous Q&A pair
                if current_question and current_answer:
                    answer = ' '.join(current_answer).strip()
                    if answer:
                        chunks.append((current_question, answer))
                
                # Start new question
                current_question = question
                current_answer = []
                continue
            
            # Check for answer markers
            answer = self._extract_marked_content(line, self.answer_markers)
            if answer:
                current_answer = [answer]
                continue
            
            # Add to current answer if we have a question
            if current_question:
                current_answer.append(line)
        
        # Add final pair
        if current_question and current_answer:
            answer = ' '.join(current_answer).strip()
            if answer:
                chunks.append((current_question, answer))
        
        return chunks
    
    def _extract_marked_content(self, line: str, markers: List[str]) -> Optional[str]:
        """Extract content after markers."""
        for marker in markers:
            if line.startswith(marker):
                return line[len(marker):].strip()
        return None


class ChunkingFactory:
    """Factory for creating chunking strategies."""
    
    _strategies = {
        ChunkingStrategy.HEADING_BASED: HeadingBasedChunker,
        ChunkingStrategy.PARAGRAPH_BASED: ParagraphBasedChunker,
        ChunkingStrategy.TOPIC_BASED: TopicBasedChunker,
        ChunkingStrategy.MANUAL_MARKERS: ManualMarkerChunker,
    }
    
    @classmethod
    def create_chunker(cls, strategy: ChunkingStrategy, **kwargs) -> ContentChunker:
        """Create a chunking strategy instance."""
        chunker_class = cls._strategies.get(strategy)
        if not chunker_class:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")
        return chunker_class(**kwargs)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available chunking strategies."""
        return [strategy.value for strategy in ChunkingStrategy]
