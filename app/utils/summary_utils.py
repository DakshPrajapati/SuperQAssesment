"""
Utility functions for summary management and slicing.
Provides methods to select appropriate summary components based on model capabilities.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.models import get_summary_size_for_model
from app.crud import thread_crud

def summary_data_to_text(summary_data: Dict[str, Any]) -> str:
    """
    Convert structured summary_data JSON to readable text format.

    Args:
        summary_data: The structured summary dictionary

    Returns:
        Formatted text representation of the summary
    """
    if not summary_data:
        return "No summary content available"

    lines = []
    if summary_data.get("core_facts"):
        lines.append("Core Facts:")
        for fact in summary_data["core_facts"]:
            lines.append(f"  • {fact}")

    if summary_data.get("user_preferences"):
        lines.append("\nUser Preferences:")
        for pref in summary_data["user_preferences"]:
            lines.append(f"  • {pref}")

    if summary_data.get("decisions_made"):
        lines.append("\nDecisions Made:")
        for decision in summary_data["decisions_made"]:
            lines.append(f"  • {decision}")

    if summary_data.get("constraints"):
        lines.append("\nConstraints:")
        for constraint in summary_data["constraints"]:
            lines.append(f"  • {constraint}")

    if summary_data.get("open_questions"):
        lines.append("\nOpen Questions:")
        for question in summary_data["open_questions"]:
            lines.append(f"  • {question}")

    if summary_data.get("entities"):
        lines.append("\nKey Entities:")
        for name, info in summary_data["entities"].items():
            lines.append(f"  • {name}: {info}")

    return "\n".join(lines) if lines else "No summary content available"


class SummarySlicingEngine:
    """
    Engine for intelligently slicing summaries based on model metadata and context.
    
    Handles:
    - Slicing summaries for different model sizes
    - Selecting summaries based on model capabilities
    - Formatting summaries for context injection
    """
    
    # Summary type definitions
    SUMMARY_TYPES = {
        "small": {
            "description": "Minimal summary for token-constrained models",
            "fields": ["core_facts", "user_preferences"]
        },
        "medium": {
            "description": "Balanced summary for most models",
            "fields": ["core_facts", "user_preferences", "decisions_made", "constraints", "open_questions"]
        },
        "large": {
            "description": "Complete summary with all information",
            "fields": ["core_facts", "user_preferences", "decisions_made", "constraints", "open_questions", "entities"]
        }
    }
    
    @staticmethod
    def slice_summary(
        summary: Dict[str, Any],
        summary_type: str = "medium"
    ) -> Dict[str, Any]:
        """
        Slice a summary based on the specified type.
        
        Args:
            summary: The complete summary dictionary
            summary_type: Type of summary ('small', 'medium', 'large')
            
        Returns:
            Sliced summary containing only specified fields
        """
        if summary_type not in SummarySlicingEngine.SUMMARY_TYPES:
            summary_type = "medium"
        
        fields = SummarySlicingEngine.SUMMARY_TYPES[summary_type]["fields"]
        sliced = {}
        
        for field in fields:
            if field in summary:
                sliced[field] = summary[field]
        
        return sliced
    
    @staticmethod
    def format_summary_for_context(
        summary: Dict[str, Any],
        summary_type: str = "medium"
    ) -> str:
        """
        Format a summary for injection as context in LLM prompts.
        
        Args:
            summary: The summary dictionary
            summary_type: Type of summary to use
            
        Returns:
            Formatted summary string for use in prompts
        """
        sliced = SummarySlicingEngine.slice_summary(summary, summary_type)
        
        lines = ["[CONVERSATION SUMMARY]"]
        
        for field, value in sliced.items():
            # Format field name (core_facts -> Core Facts)
            field_name = " ".join(word.capitalize() for word in field.split("_"))
            
            if isinstance(value, list) and value:
                lines.append(f"\n{field_name}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict) and value:
                lines.append(f"\n{field_name}:")
                for key, val in value.items():
                    lines.append(f"  - {key}: {val}")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_summary_for_model(
        summary: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """
        Get appropriately sized summary based on model metadata.
        
        Args:
            db: Database session
            summary: The complete summary dictionary
            model_name: The model identifier
            
        Returns:
            Sliced summary appropriate for the model
        """
        
        summary_type = get_summary_size_for_model(model).value
        return SummarySlicingEngine.slice_summary(summary, summary_type)
    
    @staticmethod
    def merge_summaries(
        previous: Dict[str, Any],
        new_items: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligently merge two summaries, avoiding duplicates.
        
        Args:
            previous: The previous summary
            new_items: New items to merge in
            
        Returns:
            Merged summary
        """
        merged = {
            "core_facts": [],
            "user_preferences": [],
            "decisions_made": [],
            "constraints": [],
            "open_questions": [],
            "entities": {}
        }
        
        # Merge list fields, removing duplicates
        for field in ["core_facts", "user_preferences", "decisions_made", "constraints", "open_questions"]:
            # Convert to set to remove duplicates, then back to list
            items = set(previous.get(field, []))
            items.update(new_items.get(field, []))
            merged[field] = sorted(list(items))  # Sort for consistency
        
        # Merge entities dict
        merged["entities"] = {**previous.get("entities", {}), **new_items.get("entities", {})}
        
        return merged


def get_summary_stats(summary: Dict[str, Any]) -> Dict[str, int]:
    """
    Get statistics about a summary.
    
    Args:
        summary: The summary dictionary
        
    Returns:
        Dictionary with field counts
    """
    return {
        "core_facts": len(summary.get("core_facts", [])),
        "user_preferences": len(summary.get("user_preferences", [])),
        "decisions_made": len(summary.get("decisions_made", [])),
        "constraints": len(summary.get("constraints", [])),
        "open_questions": len(summary.get("open_questions", [])),
        "entities": len(summary.get("entities", {})),
        "total_items": (
            len(summary.get("core_facts", [])) +
            len(summary.get("user_preferences", [])) +
            len(summary.get("decisions_made", [])) +
            len(summary.get("constraints", [])) +
            len(summary.get("open_questions", [])) +
            len(summary.get("entities", {}))
        )
    }
