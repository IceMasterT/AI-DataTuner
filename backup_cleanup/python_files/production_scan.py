#!/usr/bin/env python3
"""
Production Readiness Scanner - Identifies non-production code patterns.
Scans for demos, placeholders, TODOs, mocks, stubs, and incomplete code.
"""

import os
import re
from pathlib import Path

# Patterns to identify non-production code
PATTERNS = [
    r'\bTODO\b',
    r'\bFIXME\b',
    r'\bXXX\b',
    r'\bHACK\b',
    r'\bBUG\b',
    r'\bdemo\b',
    r'\bDemo\b',
    r'\bDEMO\b',
    r'\bmock\b',
    r'\bMock\b',
    r'\bMOCK\b',
    r'\bstub\b',
    r'\bStub\b',
    r'\bSTUB\b',
    r'\bplaceholder\b',
    r'\bPlaceholder\b',
    r'\bPLACEHOLDER\b',
    r'coming soon',
    r'not implemented',
    r'NotImplemented',
    r'pass\s*#.*(?:todo|fixme|placeholder|demo|stub|mock)',
    r'raise NotImplementedError',
    r'def.*demo.*\(',
    r'class.*Demo.*:',
    r'test.*demo',
    r'\bexample\b',
    r'\bExample\b',
    r'\bEXAMPLE\b',
    r'\bsample\b',
    r'\bSample\b',
    r'\bSAMPLE\b',
    r'your-api-key',
    r'sk-.*placeholder',
    r'dummy.*key',
    r'test.*key',
    r'fake.*key'
]

def scan_file(file_path):
    """Scan a file for non-production patterns."""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip empty lines and pure comments
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            for pattern in PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Additional context checks
                    context = {
                        'line_num': i,
                        'content': line_stripped[:150],
                        'pattern': pattern,
                        'severity': 'HIGH'
                    }
                    
                    # Determine severity
                    if any(x in line.lower() for x in ['todo', 'fixme', 'placeholder', 'not implemented']):
                        context['severity'] = 'CRITICAL'
                    elif any(x in line.lower() for x in ['demo', 'mock', 'stub', 'example']):
                        context['severity'] = 'HIGH'
                    elif any(x in line.lower() for x in ['sample', 'test']):
                        context['severity'] = 'MEDIUM'
                    
                    issues.append(context)
                    break  # Only report first match per line
                    
    except Exception as e:
        issues.append({
            'line_num': 0,
            'content': f'Error reading file: {e}',
            'pattern': 'ERROR',
            'severity': 'CRITICAL'
        })
    
    return issues

def scan_all_files():
    """Scan all Python files for production readiness."""
    python_files = list(Path('.').glob('*.py'))
    
    # Exclude this scanner and test files
    python_files = [f for f in python_files if f.name not in [
        'production_scan.py', 
        'test_placeholder_replacement.py'
    ]]
    
    total_issues = 0
    files_with_issues = 0
    critical_issues = 0
    high_issues = 0
    
    print('🔍 PRODUCTION READINESS SCAN')
    print('Scanning for demos, placeholders, TODOs, mocks, stubs, and incomplete code')
    print('='*80)
    
    issues_by_severity = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': []}
    
    for py_file in sorted(python_files):
        issues = scan_file(py_file)
        if issues:
            files_with_issues += 1
            print(f'\n📄 {py_file}:')
            
            for issue in issues[:15]:  # Show first 15 issues per file
                severity_icon = {
                    'CRITICAL': '🚨',
                    'HIGH': '⚠️',
                    'MEDIUM': '⚡'
                }.get(issue['severity'], '❓')
                
                print(f'   {severity_icon} Line {issue["line_num"]}: {issue["content"]}')
                issues_by_severity[issue['severity']].append((py_file, issue))
                
                if issue['severity'] == 'CRITICAL':
                    critical_issues += 1
                elif issue['severity'] == 'HIGH':
                    high_issues += 1
                
                total_issues += 1
            
            if len(issues) > 15:
                remaining = len(issues) - 15
                print(f'   ... and {remaining} more issues')
                total_issues += remaining
    
    print(f'\n📊 SCAN SUMMARY:')
    print(f'   Total Python files scanned: {len(python_files)}')
    print(f'   Files with issues: {files_with_issues}')
    print(f'   Total issues found: {total_issues}')
    print(f'   🚨 Critical issues: {critical_issues}')
    print(f'   ⚠️ High priority issues: {high_issues}')
    print(f'   ⚡ Medium priority issues: {total_issues - critical_issues - high_issues}')
    
    if total_issues == 0:
        print('\n✅ ALL FILES ARE PRODUCTION READY!')
        print('✅ No demos, placeholders, TODOs, mocks, or stubs found')
        print('✅ All code appears to be complete and functional')
        return True
    else:
        print(f'\n❌ {total_issues} ISSUES NEED TO BE FIXED FOR PRODUCTION READINESS')
        
        # Show critical issues summary
        if critical_issues > 0:
            print(f'\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:')
            for file_path, issue in issues_by_severity['CRITICAL'][:10]:
                print(f'   {file_path}:{issue["line_num"]} - {issue["content"][:100]}')
        
        return False

def scan_specific_patterns():
    """Scan for specific problematic patterns."""
    print('\n🔍 SCANNING FOR SPECIFIC PROBLEMATIC PATTERNS:')
    print('-' * 60)
    
    specific_patterns = {
        'Empty pass statements': r'^\s*pass\s*$',
        'Placeholder API keys': r'(your-api-key|sk-.*placeholder|dummy.*key)',
        'Coming soon messages': r'coming soon',
        'Not implemented': r'not implemented|NotImplemented',
        'Demo functions': r'def.*demo.*\(',
        'Test placeholders': r'# TODO|# FIXME|# XXX'
    }
    
    python_files = [f for f in Path('.').glob('*.py') if f.name != 'production_scan.py']
    
    for pattern_name, pattern in specific_patterns.items():
        matches = []
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append((py_file, i, line.strip()[:100]))
            except:
                continue
        
        if matches:
            print(f'\n⚠️ {pattern_name}: {len(matches)} found')
            for file_path, line_num, content in matches[:5]:
                print(f'   {file_path}:{line_num} - {content}')
            if len(matches) > 5:
                print(f'   ... and {len(matches) - 5} more')

if __name__ == "__main__":
    production_ready = scan_all_files()
    scan_specific_patterns()
    
    if production_ready:
        print('\n🎉 PRODUCTION SCAN COMPLETE - ALL SYSTEMS GO!')
        exit(0)
    else:
        print('\n❌ PRODUCTION SCAN FAILED - ISSUES MUST BE RESOLVED')
        exit(1)
