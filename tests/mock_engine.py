from smolagents.agents import ChatMessage
from smolagents.models import MessageRole


class MockEngine:
    def __init__(self, mocked_responses: list):
        """
        mocked_responses: A list of strings containing the text actions 
                          the agent should perform at each step.
        """
        self.responses = mocked_responses
        self.call_count = 0
        self.model_id = "mock_model"

    def generate(self, messages, stop_sequences=None, **kwargs):
        if self.call_count < len(self.responses):
            response_text = self.responses[self.call_count]
            self.call_count += 1
        else:
            response_text = "Final Answer: Evaluation completed."

        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response_text,
            tool_calls=None,
            raw=None,
            token_usage=None
        )
    
    def __call__(self, messages, stop_sequences=None, **kwargs):
        """Fallback to ensure compatibility with both invocation styles."""
        return self.generate(messages, stop_sequences, **kwargs)