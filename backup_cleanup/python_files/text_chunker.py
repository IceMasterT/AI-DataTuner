#!/usr/bin/env python3
"""
Advanced Text Chunker for Phase 2 of the pipeline.
Provides intelligent chunking with overlap control and fact extraction.
"""

import re
import nltk
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    chunk_id: int
    start_position: int
    end_position: int
    sentence_count: int
    word_count: int
    token_count: int
    overlap_with_previous: int
    fact_extracted: bool = False
    coherence_score: float = 0.0


class AdvancedChunker:
    """Advanced text chunker with overlap control and fact extraction."""
    
    def __init__(self, chunk_size: int = 150, overlap: int = 1, 
                 preserve_context: bool = True):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk
            overlap: Number of sentences to overlap between chunks
            preserve_context: Whether to preserve sentence boundaries
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.preserve_context = preserve_context
        self.logger = logging.getLogger(__name__)
        
        # Initialize sentence tokenizer
        try:
            self.sent_tokenizer = nltk.sent_tokenize
        except Exception as e:
            self.logger.warning(f"NLTK not available, using simple sentence splitting: {e}")
            self.sent_tokenizer = self._simple_sentence_split
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """Simple sentence splitting fallback."""
        # Split on sentence endings
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Simple approximation: ~0.75 tokens per word
        words = len(text.split())
        return int(words * 0.75)
    
    def _extract_facts(self, text: str) -> List[str]:
        """Extract discrete facts from text."""
        sentences = self.sent_tokenizer(text)
        facts = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Filter out very short sentences
                # Simple fact extraction - each sentence is a potential fact
                facts.append(sentence)
        
        return facts
    
    def chunk_text(self, text: str, chunk_mode: str = "sentences") -> List[str]:
        """
        Chunk text into manageable pieces.
        
        Args:
            text: Input text to chunk
            chunk_mode: "sentences", "facts", or "tokens"
            
        Returns:
            List of text chunks
        """
        if chunk_mode == "facts":
            return self._chunk_by_facts(text)
        elif chunk_mode == "tokens":
            return self._chunk_by_tokens(text)
        else:
            return self._chunk_by_sentences(text)
    
    def _chunk_by_sentences(self, text: str) -> List[str]:
        """Chunk text by sentences with overlap."""
        sentences = self.sent_tokenizer(text)
        chunks = []
        
        i = 0
        while i < len(sentences):
            chunk_sentences = []
            current_tokens = 0
            
            # Add sentences until we reach the token limit
            j = i
            while j < len(sentences) and current_tokens < self.chunk_size:
                sentence = sentences[j]
                sentence_tokens = self._estimate_tokens(sentence)
                
                if current_tokens + sentence_tokens <= self.chunk_size:
                    chunk_sentences.append(sentence)
                    current_tokens += sentence_tokens
                    j += 1
                else:
                    break
            
            if chunk_sentences:
                chunk_text = ' '.join(chunk_sentences)
                chunks.append(chunk_text)
                
                # Move forward with overlap
                sentences_in_chunk = len(chunk_sentences)
                overlap_sentences = min(self.overlap, sentences_in_chunk - 1)
                i = j - overlap_sentences
                
                if i <= j - sentences_in_chunk:  # Prevent infinite loop
                    i = j
            else:
                # Single sentence is too long, add it anyway
                if i < len(sentences):
                    chunks.append(sentences[i])
                i += 1
        
        return chunks
    
    def _chunk_by_facts(self, text: str) -> List[str]:
        """Chunk text by extracting discrete facts."""
        facts = self._extract_facts(text)
        chunks = []
        
        current_chunk = []
        current_tokens = 0
        
        for fact in facts:
            fact_tokens = self._estimate_tokens(fact)
            
            if current_tokens + fact_tokens <= self.chunk_size:
                current_chunk.append(fact)
                current_tokens += fact_tokens
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                if self.overlap > 0 and len(current_chunk) > self.overlap:
                    overlap_facts = current_chunk[-self.overlap:]
                    current_chunk = overlap_facts + [fact]
                    current_tokens = sum(self._estimate_tokens(f) for f in current_chunk)
                else:
                    current_chunk = [fact]
                    current_tokens = fact_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _chunk_by_tokens(self, text: str) -> List[str]:
        """Chunk text by token count with word boundaries."""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = []
            current_tokens = 0
            
            # Add words until we reach token limit
            while i < len(words) and current_tokens < self.chunk_size:
                word = words[i]
                word_tokens = self._estimate_tokens(word)
                
                if current_tokens + word_tokens <= self.chunk_size:
                    chunk_words.append(word)
                    current_tokens += word_tokens
                    i += 1
                else:
                    break
            
            if chunk_words:
                chunk_text = ' '.join(chunk_words)
                chunks.append(chunk_text)
                
                # Apply overlap
                if self.overlap > 0:
                    overlap_words = min(self.overlap * 10, len(chunk_words) // 2)  # ~10 words per overlap unit
                    i -= overlap_words
                    if i < 0:
                        i = 0
        
        return chunks
    
    def chunk_with_metadata(self, text: str, chunk_mode: str = "sentences") -> List[Dict[str, Any]]:
        """
        Chunk text and return with detailed metadata.
        
        Returns:
            List of dictionaries with 'text' and 'metadata' keys
        """
        chunks = self.chunk_text(text, chunk_mode)
        result = []
        
        current_position = 0
        
        for i, chunk in enumerate(chunks):
            # Calculate positions
            start_pos = text.find(chunk[:50], current_position)  # Find chunk start
            if start_pos == -1:
                start_pos = current_position
            
            end_pos = start_pos + len(chunk)
            current_position = end_pos
            
            # Calculate metrics
            sentences = self.sent_tokenizer(chunk)
            words = chunk.split()
            tokens = self._estimate_tokens(chunk)
            
            # Calculate overlap with previous chunk
            overlap_count = 0
            if i > 0 and self.overlap > 0:
                prev_chunk = chunks[i-1]
                # Simple overlap detection
                chunk_start = chunk[:100]
                if chunk_start in prev_chunk:
                    overlap_count = self.overlap
            
            metadata = ChunkMetadata(
                chunk_id=i,
                start_position=start_pos,
                end_position=end_pos,
                sentence_count=len(sentences),
                word_count=len(words),
                token_count=tokens,
                overlap_with_previous=overlap_count,
                fact_extracted=(chunk_mode == "facts")
            )
            
            result.append({
                'text': chunk,
                'metadata': metadata
            })
        
        return result
    
    def optimize_chunks_for_training(self, chunks: List[str], 
                                   target_length: int = 100) -> List[str]:
        """
        Optimize chunks for LLM training by combining or splitting as needed.
        
        Args:
            chunks: List of text chunks
            target_length: Target token length for training
            
        Returns:
            Optimized chunks
        """
        optimized = []
        current_chunk = ""
        current_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = self._estimate_tokens(chunk)
            
            if current_tokens + chunk_tokens <= target_length * 1.2:  # 20% tolerance
                # Combine chunks
                if current_chunk:
                    current_chunk += " " + chunk
                else:
                    current_chunk = chunk
                current_tokens += chunk_tokens
            else:
                # Save current and start new
                if current_chunk:
                    optimized.append(current_chunk)
                
                if chunk_tokens > target_length * 1.5:
                    # Split large chunk
                    sub_chunks = self._split_large_chunk(chunk, target_length)
                    optimized.extend(sub_chunks)
                    current_chunk = ""
                    current_tokens = 0
                else:
                    current_chunk = chunk
                    current_tokens = chunk_tokens
        
        # Add final chunk
        if current_chunk:
            optimized.append(current_chunk)
        
        return optimized
    
    def _split_large_chunk(self, chunk: str, target_length: int) -> List[str]:
        """Split a large chunk into smaller pieces."""
        sentences = self.sent_tokenizer(chunk)
        sub_chunks = []
        current_sub_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens <= target_length:
                current_sub_chunk.append(sentence)
                current_tokens += sentence_tokens
            else:
                if current_sub_chunk:
                    sub_chunks.append(' '.join(current_sub_chunk))
                current_sub_chunk = [sentence]
                current_tokens = sentence_tokens
        
        if current_sub_chunk:
            sub_chunks.append(' '.join(current_sub_chunk))
        
        return sub_chunks
    
    def get_chunking_stats(self, text: str, chunk_mode: str = "sentences") -> Dict[str, Any]:
        """Get statistics about chunking results."""
        chunks_with_metadata = self.chunk_with_metadata(text, chunk_mode)
        
        if not chunks_with_metadata:
            return {}
        
        chunk_lengths = [len(item['text']) for item in chunks_with_metadata]
        token_counts = [item['metadata'].token_count for item in chunks_with_metadata]
        
        stats = {
            "total_chunks": len(chunks_with_metadata),
            "total_characters": len(text),
            "average_chunk_length": sum(chunk_lengths) / len(chunk_lengths),
            "average_tokens_per_chunk": sum(token_counts) / len(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "overlap_setting": self.overlap,
            "chunk_mode": chunk_mode,
            "chunks_with_overlap": sum(1 for item in chunks_with_metadata 
                                     if item['metadata'].overlap_with_previous > 0)
        }
        
        return stats


def main():
    """Test the chunker."""
    sample_text = """
    Machine learning is a method of data analysis that automates analytical model building. 
    It is a branch of artificial intelligence based on the idea that systems can learn from data, 
    identify patterns and make decisions with minimal human intervention. Machine learning algorithms 
    build a model based on training data in order to make predictions or decisions without being 
    explicitly programmed to do so. Machine learning algorithms are used in a wide variety of 
    applications, such as in medicine, email filtering, speech recognition, and computer vision, 
    where it is difficult or unfeasible to develop conventional algorithms to perform the needed tasks.
    """
    
    chunker = AdvancedChunker(chunk_size=50, overlap=1)
    
    print("=== Sentence-based Chunking ===")
    chunks = chunker.chunk_text(sample_text, "sentences")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk}")
    
    print("\n=== Chunking Statistics ===")
    stats = chunker.get_chunking_stats(sample_text, "sentences")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
