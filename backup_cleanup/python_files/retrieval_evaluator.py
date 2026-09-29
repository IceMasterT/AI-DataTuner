#!/usr/bin/env python3
"""
Retrieval Evaluator & Comparison Benchmark - Instruction 7: Compare retrieval before and after.

Runs evaluation benchmark on:
- Baseline (naive chunking: split by sentences/chars, repeated furniture included, missing context prefix, severed tips)
- New Pipeline (structure-aware chunking: section hierarchy, cleaned furniture, contextual prefixes, tip preservation)

Uses benchmark test queries:
- "What are the four goal-setting tips?"
- "How do I build an audience persona?"

Evaluates Top-5 retrieved results with identical similarity metric (TF-IDF / BM25 / dense vector cosine similarity)
measuring:
1. Completeness Score (all 4 tips present in top results)
2. Context Lineage Score (hierarchy prefix present)
3. Noise Reduction (absence of repeated running headers/footers)
4. Section Boundary Purity (no unrelated section bleed)
"""

import math
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from structured_chunker import StructuredChunk

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Individual retrieval result for a query."""
    rank: int
    chunk_id: str
    score: float
    text_preview: str
    section_path: str
    has_furniture_noise: bool
    contains_required_answers: List[str]
    is_pure_section: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryBenchmarkReport:
    """Benchmark report for a single query."""
    query: str
    system_name: str  # "Baseline (Before)" or "Structure-Aware (After)"
    top_5_results: List[QueryResult]
    completeness_score: float  # 0.0 to 1.0 (fraction of expected key facts found in top 5)
    context_preservation_score: float  # 0.0 to 1.0
    noise_freedom_score: float  # 1.0 = no furniture noise in top 5
    section_purity_score: float  # 1.0 = no cross-section leakage in top 5
    top_1_hit: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "system_name": self.system_name,
            "completeness_score": f"{self.completeness_score * 100:.1f}%",
            "context_preservation_score": f"{self.context_preservation_score * 100:.1f}%",
            "noise_freedom_score": f"{self.noise_freedom_score * 100:.1f}%",
            "section_purity_score": f"{self.section_purity_score * 100:.1f}%",
            "top_1_hit": self.top_1_hit,
            "top_5_results": [r.to_dict() for r in self.top_5_results]
        }


@dataclass
class ComparisonReport:
    """Full side-by-side comparison report."""
    benchmark_timestamp: str
    queries_evaluated: int
    baseline_summary: Dict[str, float]
    structured_summary: Dict[str, float]
    detailed_comparisons: List[Dict[str, Any]]
    improvement_highlights: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_timestamp": self.benchmark_timestamp,
            "queries_evaluated": self.queries_evaluated,
            "baseline_summary": {k: f"{v*100:.1f}%" for k, v in self.baseline_summary.items()},
            "structured_summary": {k: f"{v*100:.1f}%" for k, v in self.structured_summary.items()},
            "improvement_highlights": self.improvement_highlights,
            "detailed_comparisons": self.detailed_comparisons
        }


class RetrievalEngine:
    """Consistent, deterministic retrieval engine for before/after comparison."""

    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.doc_freqs = self._compute_doc_freqs()
        self.total_docs = len(chunks)

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', text)]

    def _compute_doc_freqs(self) -> Dict[str, int]:
        df: Dict[str, int] = {}
        for c in self.chunks:
            text = c.get("embedding_text") or c.get("text", "")
            unique_terms = set(self._tokenize(text))
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1
        return df

    def query(self, query_text: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Compute BM25 / TF-IDF relevance score for query against corpus."""
        q_terms = self._tokenize(query_text)
        if not q_terms or self.total_docs == 0:
            return []

        scored = []
        for c in self.chunks:
            text = c.get("embedding_text") or c.get("text", "")
            doc_terms = self._tokenize(text)
            doc_len = len(doc_terms)
            if doc_len == 0:
                continue

            score = 0.0
            for qt in q_terms:
                tf = doc_terms.count(qt)
                if tf > 0:
                    df = self.doc_freqs.get(qt, 1)
                    idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
                    # BM25 term weighting
                    k1 = 1.2
                    b = 0.75
                    avg_len = 150.0
                    tf_norm = (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / avg_len)))
                    score += idf * tf_norm

            scored.append((c, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class RetrievalBenchmarkEvaluator:
    """Benchmark harness comparing baseline vs structured retrieval performance."""

    BENCHMARK_CASES = [
        {
            "query": "What are the four goal-setting tips?",
            "expected_elements": [
                "Make It Medium To Long Term",
                "Financial",
                "Non-Financial",
                "Be Realistic"
            ],
            "target_section": "Step One"
        },
        {
            "query": "How do I build an audience persona?",
            "expected_elements": [
                "Audience",
                "Persona",
                "Demographics",
                "Target"
            ],
            "target_section": "Step Two"
        }
    ]

    RUNNING_FURNITURE_SAMPLES = [
        "Tent Social Marketing Strategy Series",
        "Social Media Strategy Blueprint",
        "Page 1", "Page 2", "Page 3"
    ]

    _furniture: List[str] = RUNNING_FURNITURE_SAMPLES

    STOPWORDS = frozenset(
        "the and for that with this from have are was were will your you not but can all any "
        "their they them then than there these those which what when where how why into out "
        "about over more most some such also just only very been being has had its our".split()
    )

    @staticmethod
    def naive_chunk_text(text: str, size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
        """Baseline chunker: fixed-size character windows over raw text.

        No cleaning, no section awareness, no context prefix - what a
        straightforward pipeline would do with the same extracted text.
        """
        step = max(1, size - overlap)
        chunks = []
        for i, start in enumerate(range(0, len(text), step)):
            piece = text[start:start + size].strip()
            if piece:
                chunks.append({"chunk_id": f"naive_{i:03d}", "text": piece, "embedding_text": piece})
        return chunks

    @classmethod
    def build_cases_from_hierarchy(cls, hierarchy: Any, max_cases: int = 6) -> List[Dict[str, Any]]:
        """Derive benchmark queries from the document's own sections.

        For each content section: the query asks about the section's title, and the
        expected elements are the terms most distinctive to that section (frequent
        there, rare in other sections). Sections with no usable terms are skipped.
        """
        sections = [
            sec for sec in hierarchy.all_sections
            if sec.section_type in ("section", "subsection")
            and sum(len(b.text) for b in sec.blocks) >= 200
        ]
        if not sections:
            return []

        term_counts: List[Dict[str, int]] = []
        for sec in sections:
            counts: Dict[str, int] = {}
            for w in re.findall(r"[A-Za-z][A-Za-z-]{4,}", " ".join(b.text for b in sec.blocks).lower()):
                if w not in cls.STOPWORDS:
                    counts[w] = counts.get(w, 0) + 1
            term_counts.append(counts)

        n = len(sections)
        df: Dict[str, int] = {}
        for counts in term_counts:
            for w in counts:
                df[w] = df.get(w, 0) + 1

        cases = []
        for sec, counts in zip(sections, term_counts):
            ranked = sorted(counts, key=lambda w: counts[w] * math.log((n + 1) / df[w]), reverse=True)
            # Terms shared by every section can't discriminate; skip them when possible
            distinctive = [w for w in ranked if df[w] < n] or ranked
            expected = distinctive[:4]
            if len(expected) < 2:
                continue
            cases.append({
                "query": f"What does the section '{sec.title}' cover?",
                "expected_elements": expected,
                "target_section": sec.title,
            })

        # Spread the sample across the document instead of taking only the first sections
        if len(cases) > max_cases:
            stride = len(cases) / max_cases
            cases = [cases[int(i * stride)] for i in range(max_cases)]
        return cases

    def evaluate_comparison(
        self,
        baseline_chunks: List[Dict[str, Any]],
        structured_chunks: List[StructuredChunk],
        cases: Optional[List[Dict[str, Any]]] = None,
        furniture_samples: Optional[List[str]] = None,
    ) -> ComparisonReport:
        """Run benchmark on both baseline and structured chunk sets.

        `cases` and `furniture_samples` default to the built-in synthetic benchmark;
        pass document-specific ones to benchmark a real file.
        """
        cases = cases if cases is not None else self.BENCHMARK_CASES
        if not cases:
            raise ValueError("No benchmark cases: the document has no sections large enough to derive queries from")
        self._furniture = (
            furniture_samples if furniture_samples is not None else self.RUNNING_FURNITURE_SAMPLES
        )
        structured_dict_chunks = [c.to_dict() for c in structured_chunks]

        baseline_engine = RetrievalEngine(baseline_chunks)
        structured_engine = RetrievalEngine(structured_dict_chunks)

        baseline_reports: List[QueryBenchmarkReport] = []
        structured_reports: List[QueryBenchmarkReport] = []

        for case in cases:
            q = case["query"]
            expected = case["expected_elements"]
            target_sec = case["target_section"]

            # Evaluate Baseline
            base_results = baseline_engine.query(q, top_k=5)
            base_report = self._evaluate_query_results(
                q, "Baseline (Before)", base_results, expected, target_sec
            )
            baseline_reports.append(base_report)

            # Evaluate Structured
            struct_results = structured_engine.query(q, top_k=5)
            struct_report = self._evaluate_query_results(
                q, "Structure-Aware (After)", struct_results, expected, target_sec
            )
            structured_reports.append(struct_report)

        # Calculate macro averages
        base_avg_comp = sum(r.completeness_score for r in baseline_reports) / len(baseline_reports)
        base_avg_ctx = sum(r.context_preservation_score for r in baseline_reports) / len(baseline_reports)
        base_avg_noise = sum(r.noise_freedom_score for r in baseline_reports) / len(baseline_reports)
        base_avg_purity = sum(r.section_purity_score for r in baseline_reports) / len(baseline_reports)

        struct_avg_comp = sum(r.completeness_score for r in structured_reports) / len(structured_reports)
        struct_avg_ctx = sum(r.context_preservation_score for r in structured_reports) / len(structured_reports)
        struct_avg_noise = sum(r.noise_freedom_score for r in structured_reports) / len(structured_reports)
        struct_avg_purity = sum(r.section_purity_score for r in structured_reports) / len(structured_reports)

        def _delta(label: str, before: float, after: float) -> str:
            direction = "improved" if after > before else "regressed" if after < before else "unchanged"
            return f"{label} {direction}: {before*100:.1f}% -> {after*100:.1f}%."

        highlights = [
            _delta("Completeness (expected facts found in top 5)", base_avg_comp, struct_avg_comp),
            _delta("Context lineage (Document > Section breadcrumbs)", base_avg_ctx, struct_avg_ctx),
            _delta("Noise freedom (no running headers/footers)", base_avg_noise, struct_avg_noise),
            _delta("Section boundary purity (no cross-step bleed)", base_avg_purity, struct_avg_purity),
        ]

        detailed = []
        for b_rep, s_rep in zip(baseline_reports, structured_reports):
            detailed.append({
                "query": b_rep.query,
                "baseline": b_rep.to_dict(),
                "structured": s_rep.to_dict(),
                "delta_completeness": f"{(s_rep.completeness_score - b_rep.completeness_score)*100:+.1f}%"
            })

        return ComparisonReport(
            benchmark_timestamp=datetime.now().isoformat(),
            queries_evaluated=len(cases),
            baseline_summary={
                "completeness": base_avg_comp,
                "context_preservation": base_avg_ctx,
                "noise_freedom": base_avg_noise,
                "section_purity": base_avg_purity
            },
            structured_summary={
                "completeness": struct_avg_comp,
                "context_preservation": struct_avg_ctx,
                "noise_freedom": struct_avg_noise,
                "section_purity": struct_avg_purity
            },
            detailed_comparisons=detailed,
            improvement_highlights=highlights
        )

    def _evaluate_query_results(
        self,
        query: str,
        system_name: str,
        results: List[Tuple[Dict[str, Any], float]],
        expected_elements: List[str],
        target_section: str
    ) -> QueryBenchmarkReport:
        query_results: List[QueryResult] = []
        found_elements_across_top5: Set[str] = set()
        noise_free_count = 0
        pure_count = 0
        context_count = 0

        for rank, (chunk_data, score) in enumerate(results, 1):
            text = chunk_data.get("source_text") or chunk_data.get("text", "")
            emb_text = chunk_data.get("embedding_text") or text
            sec_path = chunk_data.get("section_path", "")

            # Check furniture noise
            has_noise = any(f.lower() in text.lower() for f in self._furniture)
            if not has_noise:
                noise_free_count += 1

            # Check expected elements in this chunk
            chunk_elements = [el for el in expected_elements if el.lower() in text.lower()]
            found_elements_across_top5.update(chunk_elements)

            # Check section purity (doesn't mix multiple steps)
            step_mentions = len(set(
                m.lower() for m in re.findall(r'\b(?:Step|Chapter|Part|Module)\s+[0-9A-Za-z]+', text, re.IGNORECASE)
            ))
            is_pure = step_mentions <= 1
            if is_pure:
                pure_count += 1

            # Check context
            if "Document:" in emb_text or "Section:" in emb_text or sec_path:
                context_count += 1

            query_results.append(QueryResult(
                rank=rank,
                chunk_id=chunk_data.get("chunk_id", f"c_{rank}"),
                score=round(score, 3),
                text_preview=text[:120].replace('\n', ' '),
                section_path=sec_path,
                has_furniture_noise=has_noise,
                contains_required_answers=chunk_elements,
                is_pure_section=is_pure
            ))

        total_res = max(1, len(results))
        completeness = len(found_elements_across_top5) / len(expected_elements) if expected_elements else 1.0
        top_1_hit = len(query_results) > 0 and len(query_results[0].contains_required_answers) > 0

        return QueryBenchmarkReport(
            query=query,
            system_name=system_name,
            top_5_results=query_results,
            completeness_score=completeness,
            context_preservation_score=context_count / total_res,
            noise_freedom_score=noise_free_count / total_res,
            section_purity_score=pure_count / total_res,
            top_1_hit=top_1_hit
        )
