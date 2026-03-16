#!/usr/bin/env python3
"""
Custom Personality Manager for handling user-defined personalities.
Integrates with .env configuration and provides easy personality management.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from env_config import get_config
from personality_modifier import PersonalityTemplate


@dataclass
class CustomPersonality:
    """Represents a custom personality configuration."""
    name: str
    description: str
    strength: float = 0.7
    preserve_meaning: bool = True
    tags: List[str] = None
    created_date: str = None
    last_used: str = None
    usage_count: int = 0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = ["custom"]
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()


class CustomPersonalityManager:
    """Manages custom personalities from .env and user configurations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        self.custom_personalities: Dict[str, CustomPersonality] = {}
        self.personalities_file = Path("custom_personalities.json")
        
        # Load personalities from various sources
        self._load_env_personalities()
        self._load_file_personalities()
    
    def _load_env_personalities(self):
        """Load custom personalities from .env configuration."""
        # Load single custom personality description
        if self.config.custom_personality_description:
            env_personality = CustomPersonality(
                name="env_custom",
                description=self.config.custom_personality_description,
                strength=self.config.personality_strength,
                preserve_meaning=self.config.personality_preserve_meaning,
                tags=["env", "custom"]
            )
            self.custom_personalities["env_custom"] = env_personality
            self.logger.info("Loaded custom personality from CUSTOM_PERSONALITY_DESCRIPTION")
        
        # Load multiple custom personalities from JSON
        if self.config.custom_personalities:
            for name, description in self.config.custom_personalities.items():
                if isinstance(description, str):
                    personality = CustomPersonality(
                        name=name,
                        description=description,
                        strength=self.config.personality_strength,
                        preserve_meaning=self.config.personality_preserve_meaning,
                        tags=["env", "custom"]
                    )
                    self.custom_personalities[name] = personality
                elif isinstance(description, dict):
                    # Advanced configuration
                    personality = CustomPersonality(
                        name=name,
                        description=description.get("description", ""),
                        strength=description.get("strength", self.config.personality_strength),
                        preserve_meaning=description.get("preserve_meaning", self.config.personality_preserve_meaning),
                        tags=description.get("tags", ["env", "custom"])
                    )
                    self.custom_personalities[name] = personality
            
            self.logger.info(f"Loaded {len(self.config.custom_personalities)} personalities from CUSTOM_PERSONALITIES")
    
    def _load_file_personalities(self):
        """Load custom personalities from file."""
        if self.personalities_file.exists():
            try:
                with open(self.personalities_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for name, personality_data in data.items():
                    if name not in self.custom_personalities:  # Don't override env personalities
                        personality = CustomPersonality(
                            name=name,
                            description=personality_data.get("description", ""),
                            strength=personality_data.get("strength", 0.7),
                            preserve_meaning=personality_data.get("preserve_meaning", True),
                            tags=personality_data.get("tags", ["file", "custom"]),
                            created_date=personality_data.get("created_date"),
                            last_used=personality_data.get("last_used"),
                            usage_count=personality_data.get("usage_count", 0)
                        )
                        self.custom_personalities[name] = personality
                
                self.logger.info(f"Loaded {len(data)} personalities from {self.personalities_file}")
            
            except Exception as e:
                self.logger.error(f"Error loading personalities file: {e}")
    
    def get_personality(self, name: str) -> Optional[CustomPersonality]:
        """Get a custom personality by name."""
        return self.custom_personalities.get(name)
    
    def list_personalities(self) -> List[str]:
        """List all available custom personality names."""
        return list(self.custom_personalities.keys())
    
    def get_personalities_by_tag(self, tag: str) -> List[CustomPersonality]:
        """Get personalities that have a specific tag."""
        return [p for p in self.custom_personalities.values() if tag in p.tags]
    
    def add_personality(self, personality: CustomPersonality, save_to_file: bool = True) -> bool:
        """Add a new custom personality."""
        try:
            self.custom_personalities[personality.name] = personality

            if save_to_file:
                self._save_personalities_file()

            self.logger.info(f"Added custom personality: {personality.name}")
            return True

        except Exception as e:
            self.logger.error(f"Error adding personality: {e}")
            return False

    def save_personality(self, personality: CustomPersonality) -> bool:
        """Save a custom personality (alias for add_personality)."""
        return self.add_personality(personality, save_to_file=True)
    
    def update_personality(self, name: str, **kwargs) -> bool:
        """Update an existing personality."""
        if name not in self.custom_personalities:
            return False
        
        try:
            personality = self.custom_personalities[name]
            
            for key, value in kwargs.items():
                if hasattr(personality, key):
                    setattr(personality, key, value)
            
            self._save_personalities_file()
            self.logger.info(f"Updated personality: {name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating personality: {e}")
            return False
    
    def delete_personality(self, name: str) -> bool:
        """Delete a custom personality."""
        if name not in self.custom_personalities:
            return False
        
        try:
            # Don't delete env personalities
            personality = self.custom_personalities[name]
            if "env" in personality.tags:
                self.logger.warning(f"Cannot delete env personality: {name}")
                return False
            
            del self.custom_personalities[name]
            self._save_personalities_file()
            self.logger.info(f"Deleted personality: {name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error deleting personality: {e}")
            return False
    
    def record_usage(self, name: str):
        """Record usage of a personality."""
        if name in self.custom_personalities:
            personality = self.custom_personalities[name]
            personality.last_used = datetime.now().isoformat()
            personality.usage_count += 1
            
            # Only save if it's not an env personality
            if "env" not in personality.tags:
                self._save_personalities_file()
    
    def _save_personalities_file(self):
        """Save personalities to file (excluding env personalities)."""
        try:
            file_personalities = {
                name: asdict(personality)
                for name, personality in self.custom_personalities.items()
                if "env" not in personality.tags  # Save all except env personalities
            }
            
            with open(self.personalities_file, 'w', encoding='utf-8') as f:
                json.dump(file_personalities, f, indent=2)
            
            self.logger.debug(f"Saved {len(file_personalities)} personalities to file")
        
        except Exception as e:
            self.logger.error(f"Error saving personalities file: {e}")
    
    def create_personality_from_description(self, name: str, description: str, 
                                          strength: float = 0.7, tags: List[str] = None) -> bool:
        """Create a new personality from a description."""
        if tags is None:
            tags = ["custom", "user-created"]
        
        personality = CustomPersonality(
            name=name,
            description=description,
            strength=strength,
            tags=tags
        )
        
        return self.add_personality(personality)
    
    def get_personality_for_processing(self, name_or_description: str) -> Optional[str]:
        """
        Get personality description for processing.
        Can be a personality name or direct description.
        """
        # First check if it's a custom personality name
        if name_or_description in self.custom_personalities:
            personality = self.custom_personalities[name_or_description]
            self.record_usage(name_or_description)
            return personality.description
        
        # If not found and it's a longer string, treat as direct description
        if len(name_or_description) > 20:  # Assume descriptions are longer than names
            return name_or_description
        
        return None
    
    def get_personality_suggestions(self, query: str) -> List[str]:
        """Get personality suggestions based on a query."""
        query_lower = query.lower()
        suggestions = []
        
        for name, personality in self.custom_personalities.items():
            # Check name match
            if query_lower in name.lower():
                suggestions.append(name)
                continue
            
            # Check description match
            if query_lower in personality.description.lower():
                suggestions.append(name)
                continue
            
            # Check tags match
            if any(query_lower in tag.lower() for tag in personality.tags):
                suggestions.append(name)
        
        return suggestions
    
    def export_personalities(self, file_path: str) -> bool:
        """Export all personalities to a file."""
        try:
            export_data = {
                name: asdict(personality)
                for name, personality in self.custom_personalities.items()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported {len(export_data)} personalities to {file_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error exporting personalities: {e}")
            return False
    
    def import_personalities(self, file_path: str, overwrite: bool = False) -> int:
        """Import personalities from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_count = 0
            
            for name, personality_data in import_data.items():
                if name in self.custom_personalities and not overwrite:
                    continue
                
                personality = CustomPersonality(
                    name=name,
                    description=personality_data.get("description", ""),
                    strength=personality_data.get("strength", 0.7),
                    preserve_meaning=personality_data.get("preserve_meaning", True),
                    tags=personality_data.get("tags", ["imported"]),
                    created_date=personality_data.get("created_date"),
                    last_used=personality_data.get("last_used"),
                    usage_count=personality_data.get("usage_count", 0)
                )
                
                self.custom_personalities[name] = personality
                imported_count += 1
            
            if imported_count > 0:
                self._save_personalities_file()
            
            self.logger.info(f"Imported {imported_count} personalities from {file_path}")
            return imported_count
        
        except Exception as e:
            self.logger.error(f"Error importing personalities: {e}")
            return 0
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for personalities."""
        total_personalities = len(self.custom_personalities)
        env_personalities = len([p for p in self.custom_personalities.values() if "env" in p.tags])
        file_personalities = len([p for p in self.custom_personalities.values() if "file" in p.tags])
        
        most_used = max(
            self.custom_personalities.values(),
            key=lambda p: p.usage_count,
            default=None
        )
        
        return {
            "total_personalities": total_personalities,
            "env_personalities": env_personalities,
            "file_personalities": file_personalities,
            "most_used": most_used.name if most_used else None,
            "most_used_count": most_used.usage_count if most_used else 0,
            "personalities": {
                name: {
                    "usage_count": p.usage_count,
                    "last_used": p.last_used,
                    "tags": p.tags
                }
                for name, p in self.custom_personalities.items()
            }
        }


# Global instance
_custom_personality_manager = None


def get_custom_personality_manager() -> CustomPersonalityManager:
    """Get the global custom personality manager instance."""
    global _custom_personality_manager
    
    if _custom_personality_manager is None:
        _custom_personality_manager = CustomPersonalityManager()
    
    return _custom_personality_manager
