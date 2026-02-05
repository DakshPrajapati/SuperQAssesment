"""
Summarization Service for automatic conversation summarization.
Uses LLM to generate structured summaries of chat conversations.
"""

from typing import List, Dict, Any
import json
from app.services.llm_service import LLMService
from app.core.config import settings


class SummarizationService:
    """
    Service for summarizing conversations with structured output.
    
    Generates sophisticated summaries organized into:
    - core_facts: Fundamental facts discussed
    - user_preferences: User preferences mentioned
    - decisions_made: Decisions that were made
    - constraints: Constraints or limitations
    - open_questions: Unresolved questions
    - entities: Relevant entities (people, companies, etc.)
    """
    
    def __init__(self, llm_service: LLMService = None):
        """
        Initialize the Summarization Service.
        
        Args:
            llm_service: LLMService instance. If not provided, creates a new one.
        """
        self.llm_service = llm_service or LLMService()
        self.summarization_model = settings.summarization_model
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        previous_summary: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured summary of a conversation.
        
        Args:
            messages: List of messages with 'sender', 'role', and 'content' keys
            previous_summary: Optional previous summary dict to build upon
            
        Returns:
            Dictionary with structured summary containing:
            {
                "core_facts": [],
                "user_preferences": [],
                "decisions_made": [],
                "constraints": [],
                "open_questions": [],
                "entities": {}
            }
            
        Raises:
            Exception: If summarization fails
        """
        if not messages:
            return self._empty_summary()
        
        # Format conversation for summarization
        conversation_text = "\n".join([
            f"{msg['sender']} ({msg['role']}): {msg['content']}"
            for msg in messages
        ])
        
        system_prompt = """You are a sophisticated AI that creates structured, comprehensive summaries 
of chat conversations. Analyze the conversation and extract information into these categories:

1. core_facts: List of fundamental facts, data, or information discussed
2. user_preferences: User's preferences, requirements, or stated preferences
3. decisions_made: Any decisions or conclusions that were reached
4. constraints: Limitations, constraints, or requirements mentioned
5. open_questions: Questions that remain unanswered or need follow-up
6. entities: Dictionary of important entities (people, companies, projects, etc.) with their roles
7. unlabeled: Important or notable points that don't fit the above categories

SOFT LIMIT: Keep each category concise. Prioritize quality over quantity. Aim for 3-5 items per list category.
For unlabeled, include only truly significant items that would be lost otherwise.

Respond ONLY with a valid JSON object matching this exact structure:
{
    "core_facts": [],
    "user_preferences": [],
    "decisions_made": [],
    "constraints": [],
    "open_questions": [],
    "entities": {},
    "unlabeled": []
}

All fields must be lists or dicts (as specified). Return ONLY the JSON, no additional text.
IMPORTANT: Give priority to output format.
"""
        
        # Build the prompt
        user_message = f"Please analyze and summarize this conversation:\n\n{conversation_text}"
        
        if previous_summary:
            user_message = (
                f"Here's the previous summary:\n{json.dumps(previous_summary, indent=2)}\n\n"
                f"Now, please update and refine this summary based on these new messages:\n\n"
                f"{conversation_text}\n\n"
                f"Merge the information appropriately, updating lists with new items and maintaining entity info."
            )
        
        messages_for_llm = [
            {
                "role": "user",
                "content": user_message
            }
        ]

        print(messages_for_llm)
        
        try:
            response = await self.llm_service.generate_response(
                model=self.summarization_model,
                system_prompt=system_prompt,
                messages=messages_for_llm,
                max_message_length=50000
            )
            print(response)

            # `generate_response` returns `(text, token_info)`. Accept either a tuple
            # or a plain string for compatibility, and parse the textual part.
            if isinstance(response, (list, tuple)) and len(response) > 0:
                response_text = response[0]
            else:
                response_text = response
            
            # Parse the JSON response text
            summary_data = json.loads(response_text)
            
            # Validate and ensure all required fields exist
            summary_data = self._validate_summary_structure(summary_data)
            
            return summary_data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {str(e)}")
            # Return empty summary on parse failure
            return self._empty_summary()
        except Exception as e:
            print(f"Summarization error: {str(e)}")
            raise Exception(f"Failed to summarize conversation: {str(e)}")
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return an empty summary structure."""
        return {
            "core_facts": [],
            "user_preferences": [],
            "decisions_made": [],
            "constraints": [],
            "open_questions": [],
            "entities": {},
            "unlabeled": []
        }
    
    def _validate_summary_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean summary structure, ensuring all required fields exist.
        
        Args:
            data: The summary data to validate
            
        Returns:
            Valid summary structure
        """
        required_fields = {
            "core_facts": [],
            "user_preferences": [],
            "decisions_made": [],
            "constraints": [],
            "open_questions": [],
            "entities": {},
            "unlabeled": []
        }
        
        # Ensure all required fields exist
        for field, default_value in required_fields.items():
            if field not in data:
                data[field] = default_value
            elif isinstance(default_value, list) and not isinstance(data[field], list):
                data[field] = []
            elif isinstance(default_value, dict) and not isinstance(data[field], dict):
                data[field] = {}
        
        return data
    
    def slice_summary(self, summary: Dict[str, Any], summary_type: str = "medium") -> Dict[str, Any]:
        """
        Slice a summary based on model size requirements.
        
        Args:
            summary: The full summary structure
            summary_type: Size of summary ('small', 'medium', 'large')
                - small: core_facts only
                - medium: core_facts + decisions_made + open_questions
                - large: all fields
                
        Returns:
            Sliced summary containing only relevant fields
        """
        if summary_type == "small":
            return {
                "core_facts": summary.get("core_facts", []),
                "user_preferences": summary.get("user_preferences", []),
                "constraints": summary.get("constraints", [])
            }
        elif summary_type == "medium":
            return {
                "core_facts": summary.get("core_facts", []),
                "user_preferences": summary.get("user_preferences", []),
                "decisions_made": summary.get("decisions_made", []),
                "open_questions": summary.get("open_questions", []),
                "constraints": summary.get("constraints", []),
                "unlabeled": summary.get("unlabeled", [])
            }
        else:  # large
            return summary
    
    def close(self):
        """Close the LLM service."""
        if hasattr(self, 'llm_service'):
            self.llm_service.close()
