#!/usr/bin/env python3
"""
Format conversion utilities for converting between different conversation formats.
Supports parsing and converting between various LLM training formats.
"""

import json
import re
import argparse
from typing import List, Tuple, Dict, Any, Optional
from format_templates import FormatFactory, ConversationFormat


class ConversationParser:
    """Parse conversations from different formats into a standard format."""
    
    def parse_qwen(self, text: str) -> List[Tuple[str, str]]:
        """Parse Qwen format: <|user|> content <|assistant|> content"""
        segments = []
        parts = re.split(r'<\|(user|assistant)\|>', text)
        
        current_role = None
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if part in ['user', 'assistant']:
                current_role = part
            elif current_role:
                segments.append((current_role, part))
                current_role = None
        
        return segments
    
    def parse_alpaca(self, text: str) -> List[Tuple[str, str]]:
        """Parse Alpaca format: ### Instruction: / ### Response:"""
        segments = []
        pairs = re.split(r'---+', text)  # Split by separator
        
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            
            # Extract instruction and response
            instruction_match = re.search(r'### Instruction:\s*(.+?)(?=### Response:|$)', pair, re.DOTALL)
            response_match = re.search(r'### Response:\s*(.+?)$', pair, re.DOTALL)
            
            if instruction_match and response_match:
                instruction = instruction_match.group(1).strip()
                response = response_match.group(1).strip()
                segments.extend([('user', instruction), ('assistant', response)])
        
        return segments
    
    def parse_chatml(self, text: str) -> List[Tuple[str, str]]:
        """Parse ChatML format: <|im_start|>role content<|im_end|>"""
        segments = []
        pattern = r'<\|im_start\|>(user|assistant)\s*\n(.*?)\n<\|im_end\|>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for role, content in matches:
            segments.append((role, content.strip()))
        
        return segments
    
    def parse_sharegpt(self, text: str) -> List[Tuple[str, str]]:
        """Parse ShareGPT JSON format."""
        segments = []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'role' in item and 'content' in item:
                        role = item['role']
                        if role in ['user', 'assistant']:
                            segments.append((role, item['content']))
        except json.JSONDecodeError:
            # Not JSON format, continue with other format detection
            return None
        
        return segments
    
    def parse_llama2(self, text: str) -> List[Tuple[str, str]]:
        """Parse Llama-2 format: <s>[INST] prompt [/INST] response </s>"""
        segments = []
        pattern = r'<s>\[INST\]\s*(.*?)\s*\[/INST\]\s*(.*?)\s*</s>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for instruction, response in matches:
            segments.extend([('user', instruction.strip()), ('assistant', response.strip())])
        
        return segments
    
    def parse_claude(self, text: str) -> List[Tuple[str, str]]:
        """Parse Claude format: Human: / Assistant:"""
        segments = []
        parts = re.split(r'\n\n(Human|Assistant):\s*', text)
        
        current_role = None
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if part in ['Human', 'Assistant']:
                current_role = 'user' if part == 'Human' else 'assistant'
            elif current_role:
                segments.append((current_role, part))
                current_role = None
        
        return segments
    
    def parse_minimalist(self, text: str) -> List[Tuple[str, str]]:
        """Parse minimalist format: User: / Assistant:"""
        segments = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('User: '):
                segments.append(('user', line[6:].strip()))
            elif line.startswith('Assistant: '):
                segments.append(('assistant', line[11:].strip()))
        
        return segments
    
    def auto_detect_format(self, text: str) -> Optional[ConversationFormat]:
        """Auto-detect the format of the input text."""
        text_sample = text[:1000]  # Check first 1000 characters
        
        # Check for format-specific patterns
        if '<|user|>' in text_sample or '<|assistant|>' in text_sample:
            return ConversationFormat.QWEN
        elif '<|im_start|>' in text_sample and '<|im_end|>' in text_sample:
            return ConversationFormat.CHATML
        elif '[INST]' in text_sample and '[/INST]' in text_sample:
            return ConversationFormat.LLAMA2
        elif '### Instruction:' in text_sample and '### Response:' in text_sample:
            return ConversationFormat.ALPACA
        elif 'Human:' in text_sample and 'Assistant:' in text_sample:
            return ConversationFormat.CLAUDE
        elif 'User:' in text_sample and 'Assistant:' in text_sample:
            return ConversationFormat.MINIMALIST
        elif text_sample.strip().startswith('[') or text_sample.strip().startswith('{'):
            try:
                json.loads(text_sample)
                return ConversationFormat.SHAREGPT
            except json.JSONDecodeError:
                # Not ShareGPT JSON format, continue with other format detection
                return None
        
        return None
    
    def parse_format(self, text: str, format_type: ConversationFormat) -> List[Tuple[str, str]]:
        """Parse text using the specified format."""
        parsers = {
            ConversationFormat.QWEN: self.parse_qwen,
            ConversationFormat.ALPACA: self.parse_alpaca,
            ConversationFormat.CHATML: self.parse_chatml,
            ConversationFormat.SHAREGPT: self.parse_sharegpt,
            ConversationFormat.LLAMA2: self.parse_llama2,
            ConversationFormat.CLAUDE: self.parse_claude,
            ConversationFormat.MINIMALIST: self.parse_minimalist,
        }
        
        parser = parsers.get(format_type)
        if parser:
            return parser(text)
        else:
            raise ValueError(f"Unsupported format for parsing: {format_type}")


class FormatConverter:
    """Convert between different conversation formats."""
    
    def __init__(self):
        self.parser = ConversationParser()
    
    def convert(self, text: str, source_format: str, target_format: str, **kwargs) -> str:
        """
        Convert text from one format to another.
        
        Args:
            text: Input text in source format
            source_format: Source format name
            target_format: Target format name
            **kwargs: Additional arguments for target format
            
        Returns:
            Converted text in target format
        """
        # Parse source format
        try:
            source_enum = ConversationFormat(source_format.lower())
        except ValueError:
            # Try auto-detection
            source_enum = self.parser.auto_detect_format(text)
            if not source_enum:
                raise ValueError(f"Could not detect or parse source format: {source_format}")
        
        # Parse the conversation
        segments = self.parser.parse_format(text, source_enum)
        
        if not segments:
            raise ValueError("No conversation segments found in input text")
        
        # Create target format template
        try:
            target_enum = ConversationFormat(target_format.lower())
            template = FormatFactory.create_template(target_enum, **kwargs)
        except ValueError:
            raise ValueError(f"Unsupported target format: {target_format}")
        
        # Convert to target format
        return template.format_conversation(segments)
    
    def batch_convert(self, input_files: List[str], source_format: str, 
                     target_format: str, output_dir: str = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Convert multiple files from one format to another.
        
        Args:
            input_files: List of input file paths
            source_format: Source format name
            target_format: Target format name
            output_dir: Output directory (optional)
            **kwargs: Additional arguments for target format
            
        Returns:
            List of conversion results
        """
        results = []
        
        for input_file in input_files:
            try:
                # Read input file
                with open(input_file, 'r', encoding='utf-8') as f:
                    input_text = f.read()
                
                # Convert format
                converted_text = self.convert(input_text, source_format, target_format, **kwargs)
                
                # Determine output file path
                if output_dir:
                    from pathlib import Path
                    input_path = Path(input_file)
                    output_path = Path(output_dir) / f"{input_path.stem}_{target_format}{input_path.suffix}"
                else:
                    output_path = input_file.replace('.', f'_{target_format}.')
                
                # Write output file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(converted_text)
                
                results.append({
                    'input_file': input_file,
                    'output_file': str(output_path),
                    'success': True,
                    'segments_converted': len(self.parser.parse_format(
                        input_text, 
                        ConversationFormat(source_format.lower()) if source_format != 'auto' 
                        else self.parser.auto_detect_format(input_text)
                    ))
                })
                
            except Exception as e:
                results.append({
                    'input_file': input_file,
                    'success': False,
                    'error': str(e)
                })
        
        return results


def main():
    """Main function for format conversion CLI."""
    parser = argparse.ArgumentParser(description="Convert between conversation formats")
    parser.add_argument("input", help="Input file or text")
    parser.add_argument("-s", "--source", default="auto", 
                       help="Source format (auto-detect if not specified)")
    parser.add_argument("-t", "--target", required=True,
                       choices=FormatFactory.get_available_formats(),
                       help="Target format")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--system-message", help="System message for OpenAI format")
    parser.add_argument("--batch", nargs="+", help="Batch convert multiple files")
    parser.add_argument("--output-dir", help="Output directory for batch conversion")
    
    args = parser.parse_args()
    
    converter = FormatConverter()
    
    try:
        if args.batch:
            # Batch conversion
            format_kwargs = {}
            if args.system_message and args.target == "openai":
                format_kwargs["system_message"] = args.system_message
            
            results = converter.batch_convert(
                args.batch, args.source, args.target, 
                args.output_dir, **format_kwargs
            )
            
            # Print results
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            print(f"Converted {len(successful)}/{len(results)} files successfully")
            
            if failed:
                print("\nFailed conversions:")
                for fail in failed:
                    print(f"  {fail['input_file']}: {fail['error']}")
        
        else:
            # Single file conversion
            with open(args.input, 'r', encoding='utf-8') as f:
                input_text = f.read()
            
            format_kwargs = {}
            if args.system_message and args.target == "openai":
                format_kwargs["system_message"] = args.system_message
            
            converted_text = converter.convert(input_text, args.source, args.target, **format_kwargs)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(converted_text)
                print(f"Converted text saved to: {args.output}")
            else:
                print(converted_text)
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
