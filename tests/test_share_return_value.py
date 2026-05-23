import random
import string

from smolagents import CodeAgent, Tool

from tests.mock_engine import MockEngine


class Tool1(Tool):
    name = "tool_one"
    description = \
        "This is the first tool to call. \
        It accepts the user input and transforms it. \
        The return value of this tool is the input of tool_two."
    output_type = "string"

    @property
    def inputs(self):
        return {
            "user_input": {
                "type": "string",
                "description": "This is the user input. This tool transforms the user input by appending a random string."
            }
        }
    
    def forward(self, user_input: str) -> str:
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        result = user_input + random_string
        return {
            "tool_one_result": result
        }
    
class Tool2(Tool):
    name = "tool_two"
    description = \
        "This is the second tool to call. \
        The input to this tool is the result of tool1."
    output_type = "string"

    @property
    def inputs(self):
        return {
            "tool_one_result": {
                "type": "string",
                "description": "This tool accepts the result of tool_one, applies another transformation and then returns the final result."
            }
        }
    
    def forward(self, tool_one_result: str) -> str:
        prefix = "XXXXX"
        result = prefix + tool_one_result
        return {
            "tool_two_result": result
        }


if __name__ == "__main__":
    mocked_llm_steps = [
        """
        Thought: I will first call tool1("user input string").
        Then I will use the return value of tool1 as the input to call tool2("tool_one_result").
        ```
        <code>
        tool_one_resultxxx = tool_one("some string")
        </code>
        """,
        """
        Thought: Now I will call tool2 with the return value of tool1 as its input.
        <code>
        tool_two_result = tool_two(tool_one_result)
        </code>
        """,
        """
        Thought: Now I have the result of tool2, this is the final result.
        ```
        <code>
        final_answer(f"{tool_two_result}")
        </code>
        """
    ]

    model = MockEngine(mocked_llm_steps)
    agent = CodeAgent(
        tools = [Tool2(), Tool1()],
        stream_outputs=False,
        model=model
    )
    agent.run("Dummy")
