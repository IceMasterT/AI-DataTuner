"""
Conversation format templates for different LLM training formats.
Based on the comprehensive format documentation provided.
"""

import json
from typing import List, Tuple, Dict, Any
from enum import Enum


class ConversationFormat(Enum):
    """Supported conversation formats."""
    QWEN = "qwen"
    ALPACA = "alpaca"
    CHATML = "chatml"
    SHAREGPT = "sharegpt"
    LLAMA2 = "llama2"
    ZEPHYR = "zephyr"
    INSTRUCT = "instruct"
    OPENAI = "openai"
    CLAUDE = "claude"
    MINIMALIST = "minimalist"


class FormatTemplate:
    """Base class for conversation format templates."""

    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        """Format conversation segments into the specific format."""
        if not segments:
            return ""

        formatted_parts = []
        for user_content, assistant_content in segments:
            if user_content and assistant_content:
                formatted_turn = self.format_single_turn(user_content, assistant_content)
                if formatted_turn:
                    formatted_parts.append(formatted_turn)

        return self.join_turns(formatted_parts)

    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        """Format a single Q&A turn."""
        # Default implementation - should be overridden by subclasses
        return f"User: {user_content}\nAssistant: {assistant_content}\n"

    def join_turns(self, formatted_turns: List[str]) -> str:
        """Join multiple formatted turns."""
        return "\n".join(formatted_turns)

    def clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        if not content:
            return ""

        # Remove excessive whitespace
        content = " ".join(content.split())

        # Remove leading/trailing whitespace
        content = content.strip()

        return content


class QwenTemplate(FormatTemplate):
    """Qwen standard format: <|user|> [prompt] <|assistant|> [answer]"""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_lines = []
        for role, content in segments:
            formatted_lines.append(f"<|{role}|> {content}")
        return "\n\n".join(formatted_lines)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"<|user|> {user_content}\n\n<|assistant|> {assistant_content}"


class AlpacaTemplate(FormatTemplate):
    """Alpaca/Vicuna format with ### delimiters."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_pairs = []
        current_instruction = None
        
        for role, content in segments:
            if role == "user":
                current_instruction = content
            elif role == "assistant" and current_instruction:
                pair = self.format_single_turn(current_instruction, content)
                formatted_pairs.append(pair)
                current_instruction = None
        
        return "\n\n---\n\n".join(formatted_pairs)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"### Instruction:\n{user_content}\n\n### Response:\n{assistant_content}"


class ChatMLTemplate(FormatTemplate):
    """ChatML format used by ChatGLM, some Qwen, MiniCPM."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_lines = []
        for role, content in segments:
            formatted_lines.append(f"<|im_start|>{role}\n{content}\n<|im_end|>")
        return "\n".join(formatted_lines)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"<|im_start|>user\n{user_content}\n<|im_end|>\n<|im_start|>assistant\n{assistant_content}\n<|im_end|>"


class ShareGPTTemplate(FormatTemplate):
    """ShareGPT JSON format."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        messages = []
        for role, content in segments:
            messages.append({"role": role, "content": content})
        return json.dumps(messages, indent=2, ensure_ascii=False)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
        return json.dumps(messages, indent=2, ensure_ascii=False)


class Llama2Template(FormatTemplate):
    """Llama-2 format with [INST] tokens."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_pairs = []
        current_instruction = None
        
        for role, content in segments:
            if role == "user":
                current_instruction = content
            elif role == "assistant" and current_instruction:
                pair = self.format_single_turn(current_instruction, content)
                formatted_pairs.append(pair)
                current_instruction = None
        
        return " ".join(formatted_pairs)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"<s>[INST] {user_content} [/INST] {assistant_content} </s>"


class ZephyrTemplate(FormatTemplate):
    """Zephyr/Deepseek YAML format."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        yaml_lines = []
        for role, content in segments:
            yaml_lines.append(f"- role: {role}")
            yaml_lines.append(f"  content: {content}")
        return "\n".join(yaml_lines)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"- role: user\n  content: {user_content}\n- role: assistant\n  content: {assistant_content}"


class InstructTemplate(FormatTemplate):
    """Simple Question/Answer format."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_pairs = []
        current_question = None
        
        for role, content in segments:
            if role == "user":
                current_question = content
            elif role == "assistant" and current_question:
                pair = self.format_single_turn(current_question, content)
                formatted_pairs.append(pair)
                current_question = None
        
        return "\n\n".join(formatted_pairs)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"Question: {user_content}\nAnswer: {assistant_content}"


class OpenAITemplate(FormatTemplate):
    """OpenAI API format with system message support."""
    
    def __init__(self, system_message: str = None):
        self.system_message = system_message or "You are a helpful assistant."
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        messages = [{"role": "system", "content": self.system_message}]
        for role, content in segments:
            messages.append({"role": role, "content": content})
        return json.dumps(messages, indent=2, ensure_ascii=False)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
        return json.dumps(messages, indent=2, ensure_ascii=False)


class ClaudeTemplate(FormatTemplate):
    """Claude format with Human/Assistant markers."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_lines = []
        for role, content in segments:
            role_name = "Human" if role == "user" else "Assistant"
            formatted_lines.append(f"{role_name}: {content}")
        return "\n\n".join(formatted_lines)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"Human: {user_content}\n\nAssistant: {assistant_content}"


class MinimalistTemplate(FormatTemplate):
    """Ultra-minimalist format with simple User/Assistant markers."""
    
    def format_conversation(self, segments: List[Tuple[str, str]]) -> str:
        formatted_lines = []
        for role, content in segments:
            role_name = "User" if role == "user" else "Assistant"
            formatted_lines.append(f"{role_name}: {content}")
        return "\n".join(formatted_lines)
    
    def format_single_turn(self, user_content: str, assistant_content: str) -> str:
        return f"User: {user_content}\nAssistant: {assistant_content}"


class FormatFactory:
    """Factory for creating format templates."""
    
    _templates = {
        ConversationFormat.QWEN: QwenTemplate,
        ConversationFormat.ALPACA: AlpacaTemplate,
        ConversationFormat.CHATML: ChatMLTemplate,
        ConversationFormat.SHAREGPT: ShareGPTTemplate,
        ConversationFormat.LLAMA2: Llama2Template,
        ConversationFormat.ZEPHYR: ZephyrTemplate,
        ConversationFormat.INSTRUCT: InstructTemplate,
        ConversationFormat.OPENAI: OpenAITemplate,
        ConversationFormat.CLAUDE: ClaudeTemplate,
        ConversationFormat.MINIMALIST: MinimalistTemplate,
    }
    
    @classmethod
    def create_template(cls, format_type: ConversationFormat, **kwargs) -> FormatTemplate:
        """Create a format template instance."""
        template_class = cls._templates.get(format_type)
        if not template_class:
            raise ValueError(f"Unsupported format: {format_type}")
        return template_class(**kwargs)
    
    @classmethod
    def get_available_formats(cls) -> List[str]:
        """Get list of available format names."""
        return [fmt.value for fmt in ConversationFormat]
    
    @classmethod
    def get_format_description(cls, format_type: ConversationFormat) -> str:
        """Get description of a format."""
        descriptions = {
            ConversationFormat.QWEN: "Qwen standard: <|user|> prompt <|assistant|> response",
            ConversationFormat.ALPACA: "Alpaca/Vicuna: ### Instruction: / ### Response:",
            ConversationFormat.CHATML: "ChatML: <|im_start|>role content<|im_end|>",
            ConversationFormat.SHAREGPT: "ShareGPT: JSON array with role/content objects",
            ConversationFormat.LLAMA2: "Llama-2: <s>[INST] prompt [/INST] response </s>",
            ConversationFormat.ZEPHYR: "Zephyr: YAML format with role/content pairs",
            ConversationFormat.INSTRUCT: "Simple: Question: / Answer: format",
            ConversationFormat.OPENAI: "OpenAI API: JSON with system/user/assistant roles",
            ConversationFormat.CLAUDE: "Claude: Human: / Assistant: markers",
            ConversationFormat.MINIMALIST: "Minimalist: User: / Assistant: alternating lines"
        }
        return descriptions.get(format_type, "Unknown format")
