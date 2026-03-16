#!/usr/bin/env python3
"""
Markup and code validation for detecting malformed content in training data.
Validates JSON, HTML, XML, Markdown, and other structured formats.
"""

import json
import re
import html
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse
import ast


class MarkupValidator:
    """Comprehensive markup and code validation."""
    
    def __init__(self):
        # Dangerous HTML tags and attributes
        self.dangerous_html_tags = {
            'script', 'iframe', 'object', 'embed', 'applet', 'form',
            'input', 'button', 'textarea', 'select', 'option'
        }
        
        self.dangerous_html_attributes = {
            'onclick', 'onload', 'onerror', 'onmouseover', 'onfocus',
            'onblur', 'onchange', 'onsubmit', 'href', 'src', 'action'
        }
        
        # Suspicious URL patterns
        self.suspicious_url_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file://',
            r'ftp://',
        ]
        
        # Code injection patterns
        self.injection_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'eval\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\(',
            r'Function\s*\(',
            r'document\.write',
            r'innerHTML\s*=',
            r'outerHTML\s*=',
        ]
    
    def validate_json(self, text: str) -> Dict[str, Any]:
        """Validate JSON content and detect issues."""
        result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'structure_analysis': {}
        }
        
        try:
            # Attempt to parse JSON
            parsed = json.loads(text)
            result['is_valid'] = True
            result['structure_analysis'] = self._analyze_json_structure(parsed)
            
            # Check for suspicious content in JSON values
            suspicious_content = self._check_json_content(parsed)
            if suspicious_content:
                result['warnings'].extend(suspicious_content)
                
        except json.JSONDecodeError as e:
            result['errors'].append(f"JSON parsing error: {str(e)}")
            
            # Try to identify common JSON issues
            json_issues = self._diagnose_json_issues(text)
            result['errors'].extend(json_issues)
        
        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")
        
        return result
    
    def validate_html(self, text: str) -> Dict[str, Any]:
        """Validate HTML content and detect security issues."""
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'security_issues': [],
            'structure_analysis': {}
        }
        
        # Check for dangerous tags
        dangerous_tags = self._find_dangerous_html_tags(text)
        if dangerous_tags:
            result['security_issues'].extend(dangerous_tags)
        
        # Check for dangerous attributes
        dangerous_attrs = self._find_dangerous_html_attributes(text)
        if dangerous_attrs:
            result['security_issues'].extend(dangerous_attrs)
        
        # Check for injection patterns
        injections = self._find_injection_patterns(text)
        if injections:
            result['security_issues'].extend(injections)
        
        # Check for malformed HTML
        html_issues = self._check_html_structure(text)
        result['structure_analysis'] = html_issues
        
        # Check for suspicious URLs
        suspicious_urls = self._find_suspicious_urls(text)
        if suspicious_urls:
            result['warnings'].extend(suspicious_urls)
        
        return result
    
    def validate_xml(self, text: str) -> Dict[str, Any]:
        """Validate XML content."""
        result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'structure_analysis': {}
        }
        
        try:
            # Parse XML
            root = ET.fromstring(text)
            result['is_valid'] = True
            
            # Analyze XML structure
            result['structure_analysis'] = {
                'root_tag': root.tag,
                'total_elements': len(list(root.iter())),
                'max_depth': self._calculate_xml_depth(root),
                'namespaces': list(root.nsmap.keys()) if hasattr(root, 'nsmap') else []
            }
            
            # Check for suspicious content
            suspicious_content = self._check_xml_content(root)
            if suspicious_content:
                result['warnings'].extend(suspicious_content)
                
        except ET.ParseError as e:
            result['errors'].append(f"XML parsing error: {str(e)}")
        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")
        
        return result
    
    def validate_markdown(self, text: str) -> Dict[str, Any]:
        """Validate Markdown content and detect issues."""
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'structure_analysis': {}
        }
        
        # Analyze Markdown structure
        structure = self._analyze_markdown_structure(text)
        result['structure_analysis'] = structure
        
        # Check for embedded HTML in Markdown
        html_content = self._extract_html_from_markdown(text)
        if html_content:
            for html_snippet in html_content:
                html_validation = self.validate_html(html_snippet)
                if html_validation['security_issues']:
                    result['warnings'].append(f"Embedded HTML security issue: {html_validation['security_issues']}")
        
        # Check for suspicious links
        suspicious_links = self._find_suspicious_markdown_links(text)
        if suspicious_links:
            result['warnings'].extend(suspicious_links)
        
        # Check for malformed Markdown
        markdown_issues = self._check_markdown_syntax(text)
        if markdown_issues:
            result['errors'].extend(markdown_issues)
        
        return result
    
    def validate_code(self, text: str, language: str = 'auto') -> Dict[str, Any]:
        """Validate code content for various programming languages."""
        result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'language': language,
            'structure_analysis': {}
        }
        
        # Auto-detect language if not specified
        if language == 'auto':
            language = self._detect_code_language(text)
            result['language'] = language
        
        # Language-specific validation
        if language == 'python':
            result.update(self._validate_python_code(text))
        elif language == 'javascript':
            result.update(self._validate_javascript_code(text))
        elif language == 'sql':
            result.update(self._validate_sql_code(text))
        else:
            # Generic code validation
            result.update(self._validate_generic_code(text))
        
        return result
    
    def _analyze_json_structure(self, obj: Any, depth: int = 0) -> Dict[str, Any]:
        """Analyze JSON structure for anomalies."""
        analysis = {
            'type': type(obj).__name__,
            'depth': depth,
            'size': 0
        }
        
        if isinstance(obj, dict):
            analysis['size'] = len(obj)
            analysis['keys'] = list(obj.keys())[:10]  # First 10 keys
            
            # Check for suspicious keys
            suspicious_keys = [key for key in obj.keys() if any(pattern in str(key).lower() 
                             for pattern in ['script', 'eval', 'function', 'code'])]
            if suspicious_keys:
                analysis['suspicious_keys'] = suspicious_keys
                
        elif isinstance(obj, list):
            analysis['size'] = len(obj)
            if obj:
                analysis['element_types'] = list(set(type(item).__name__ for item in obj))
        
        elif isinstance(obj, str):
            analysis['size'] = len(obj)
            # Check for code-like content in strings
            if any(pattern in obj.lower() for pattern in ['<script', 'javascript:', 'eval(']):
                analysis['contains_code'] = True
        
        return analysis
    
    def _check_json_content(self, obj: Any) -> List[str]:
        """Check JSON content for suspicious elements."""
        warnings = []
        
        def check_recursive(item, path=""):
            if isinstance(item, dict):
                for key, value in item.items():
                    current_path = f"{path}.{key}" if path else key
                    check_recursive(value, current_path)
            elif isinstance(item, list):
                for i, value in enumerate(item):
                    current_path = f"{path}[{i}]"
                    check_recursive(value, current_path)
            elif isinstance(item, str):
                # Check for suspicious content in strings
                for pattern in self.injection_patterns:
                    if re.search(pattern, item, re.IGNORECASE):
                        warnings.append(f"Suspicious content at {path}: {pattern}")
        
        check_recursive(obj)
        return warnings
    
    def _diagnose_json_issues(self, text: str) -> List[str]:
        """Diagnose common JSON formatting issues."""
        issues = []
        
        # Check for common JSON problems
        if text.count('{') != text.count('}'):
            issues.append("Unbalanced curly braces")
        
        if text.count('[') != text.count(']'):
            issues.append("Unbalanced square brackets")
        
        if text.count('"') % 2 != 0:
            issues.append("Unbalanced quotes")
        
        # Check for trailing commas
        if re.search(r',\s*[}\]]', text):
            issues.append("Trailing commas detected")
        
        # Check for single quotes (not valid JSON)
        if "'" in text:
            issues.append("Single quotes found (JSON requires double quotes)")
        
        return issues
    
    def _find_dangerous_html_tags(self, text: str) -> List[str]:
        """Find dangerous HTML tags."""
        dangerous_found = []
        
        for tag in self.dangerous_html_tags:
            pattern = f'<{tag}[^>]*>'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                dangerous_found.append(f"Dangerous tag '{tag}' found: {len(matches)} occurrences")
        
        return dangerous_found
    
    def _find_dangerous_html_attributes(self, text: str) -> List[str]:
        """Find dangerous HTML attributes."""
        dangerous_found = []
        
        for attr in self.dangerous_html_attributes:
            pattern = f'{attr}\\s*='
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                dangerous_found.append(f"Dangerous attribute '{attr}' found: {len(matches)} occurrences")
        
        return dangerous_found
    
    def _find_injection_patterns(self, text: str) -> List[str]:
        """Find code injection patterns."""
        injections_found = []
        
        for pattern in self.injection_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                injections_found.append(f"Injection pattern found: {pattern}")
        
        return injections_found
    
    def _check_html_structure(self, text: str) -> Dict[str, Any]:
        """Check HTML structure for issues."""
        analysis = {}
        
        # Count tags
        open_tags = re.findall(r'<([a-zA-Z][^>]*)>', text)
        close_tags = re.findall(r'</([a-zA-Z][^>]*)>', text)
        
        analysis['open_tags'] = len(open_tags)
        analysis['close_tags'] = len(close_tags)
        
        # Check for unbalanced tags
        tag_balance = {}
        for tag in open_tags:
            tag_name = tag.split()[0].lower()
            tag_balance[tag_name] = tag_balance.get(tag_name, 0) + 1
        
        for tag in close_tags:
            tag_name = tag.lower()
            tag_balance[tag_name] = tag_balance.get(tag_name, 0) - 1
        
        unbalanced = {tag: count for tag, count in tag_balance.items() if count != 0}
        if unbalanced:
            analysis['unbalanced_tags'] = unbalanced
        
        return analysis
    
    def _find_suspicious_urls(self, text: str) -> List[str]:
        """Find suspicious URLs in text."""
        suspicious_found = []
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+|[^\s<>"\']+\.[a-z]{2,}[^\s<>"\']*'
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        
        for url in urls:
            for pattern in self.suspicious_url_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    suspicious_found.append(f"Suspicious URL: {url}")
                    break
        
        return suspicious_found
    
    def _calculate_xml_depth(self, element, depth=0) -> int:
        """Calculate maximum depth of XML tree."""
        max_depth = depth
        for child in element:
            child_depth = self._calculate_xml_depth(child, depth + 1)
            max_depth = max(max_depth, child_depth)
        return max_depth
    
    def _check_xml_content(self, element) -> List[str]:
        """Check XML content for suspicious elements."""
        warnings = []
        
        # Check element text
        if element.text:
            for pattern in self.injection_patterns:
                if re.search(pattern, element.text, re.IGNORECASE):
                    warnings.append(f"Suspicious content in XML element: {pattern}")
        
        # Check attributes
        for attr_name, attr_value in element.attrib.items():
            for pattern in self.injection_patterns:
                if re.search(pattern, attr_value, re.IGNORECASE):
                    warnings.append(f"Suspicious content in XML attribute '{attr_name}': {pattern}")
        
        # Recursively check children
        for child in element:
            warnings.extend(self._check_xml_content(child))
        
        return warnings
    
    def _analyze_markdown_structure(self, text: str) -> Dict[str, Any]:
        """Analyze Markdown structure."""
        analysis = {}
        
        # Count headers
        headers = re.findall(r'^#{1,6}\s+(.+)$', text, re.MULTILINE)
        analysis['header_count'] = len(headers)
        
        # Count links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
        analysis['link_count'] = len(links)
        
        # Count code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        analysis['code_block_count'] = len(code_blocks)
        
        # Count inline code
        inline_code = re.findall(r'`[^`]+`', text)
        analysis['inline_code_count'] = len(inline_code)
        
        return analysis
    
    def _extract_html_from_markdown(self, text: str) -> List[str]:
        """Extract HTML content from Markdown."""
        # Find HTML tags in Markdown
        html_pattern = r'<[^>]+>.*?</[^>]+>|<[^>]+/>'
        return re.findall(html_pattern, text, re.DOTALL)
    
    def _find_suspicious_markdown_links(self, text: str) -> List[str]:
        """Find suspicious links in Markdown."""
        suspicious_found = []
        
        # Extract Markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
        
        for link_text, url in links:
            for pattern in self.suspicious_url_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    suspicious_found.append(f"Suspicious Markdown link: [{link_text}]({url})")
                    break
        
        return suspicious_found
    
    def _check_markdown_syntax(self, text: str) -> List[str]:
        """Check for Markdown syntax issues."""
        issues = []
        
        # Check for unbalanced code blocks
        triple_backticks = text.count('```')
        if triple_backticks % 2 != 0:
            issues.append("Unbalanced code blocks (```)")
        
        # Check for unbalanced inline code
        single_backticks = text.count('`')
        if single_backticks % 2 != 0:
            issues.append("Unbalanced inline code (`)")
        
        return issues
    
    def _detect_code_language(self, text: str) -> str:
        """Auto-detect programming language."""
        # Simple heuristics for language detection
        if any(keyword in text for keyword in ['def ', 'import ', 'print(', 'if __name__']):
            return 'python'
        elif any(keyword in text for keyword in ['function ', 'var ', 'const ', 'let ', 'console.log']):
            return 'javascript'
        elif any(keyword in text for keyword in ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'UPDATE']):
            return 'sql'
        else:
            return 'unknown'
    
    def _validate_python_code(self, text: str) -> Dict[str, Any]:
        """Validate Python code."""
        result = {'is_valid': False, 'errors': [], 'warnings': []}
        
        try:
            # Try to parse as AST
            ast.parse(text)
            result['is_valid'] = True
            
            # Check for dangerous functions
            dangerous_functions = ['eval', 'exec', 'compile', '__import__']
            for func in dangerous_functions:
                if func in text:
                    result['warnings'].append(f"Potentially dangerous function: {func}")
                    
        except SyntaxError as e:
            result['errors'].append(f"Python syntax error: {str(e)}")
        except Exception as e:
            result['errors'].append(f"Python validation error: {str(e)}")
        
        return result
    
    def _validate_javascript_code(self, text: str) -> Dict[str, Any]:
        """Validate JavaScript code."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Check for dangerous functions
        dangerous_functions = ['eval', 'setTimeout', 'setInterval', 'Function']
        for func in dangerous_functions:
            if func in text:
                result['warnings'].append(f"Potentially dangerous function: {func}")
        
        # Basic syntax checks
        if text.count('{') != text.count('}'):
            result['errors'].append("Unbalanced curly braces")
            result['is_valid'] = False
        
        if text.count('(') != text.count(')'):
            result['errors'].append("Unbalanced parentheses")
            result['is_valid'] = False
        
        return result
    
    def _validate_sql_code(self, text: str) -> Dict[str, Any]:
        """Validate SQL code."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Check for SQL injection patterns
        injection_patterns = [
            r';\s*DROP\s+TABLE',
            r';\s*DELETE\s+FROM',
            r'UNION\s+SELECT',
            r'--\s*',
            r'/\*.*?\*/',
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['warnings'].append(f"Potential SQL injection pattern: {pattern}")
        
        return result
    
    def _validate_generic_code(self, text: str) -> Dict[str, Any]:
        """Generic code validation."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Basic bracket balance check
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for char in text:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    result['errors'].append(f"Unmatched closing bracket: {char}")
                    result['is_valid'] = False
                else:
                    last_open = stack.pop()
                    if brackets[last_open] != char:
                        result['errors'].append(f"Mismatched brackets: {last_open} and {char}")
                        result['is_valid'] = False
        
        if stack:
            result['errors'].append(f"Unclosed brackets: {stack}")
            result['is_valid'] = False
        
        return result
