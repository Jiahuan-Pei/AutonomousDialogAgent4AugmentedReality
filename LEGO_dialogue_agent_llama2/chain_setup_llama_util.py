import os
from typing import Optional, Any
from uuid import UUID
import logging
from typing import Tuple, Dict, List
from pydantic import BaseModel, Field
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from transformers import GenerationConfig, pipeline
from huggingface_hub import login
from langchain.agents import initialize_agent
from langchain.tools import StructuredTool
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.prompts.chat import MessagesPlaceholder
from langchain.agents import AgentOutputParser, AgentType
from langchain.agents.conversational_chat.prompt import FORMAT_INSTRUCTIONS
from langchain.output_parsers.json import parse_json_markdown
from langchain.schema import AgentAction, AgentFinish
from langchain.llms import HuggingFacePipeline
from langchain.callbacks.base import BaseCallbackHandler
from langchain.agents import tool
from langchain.agents.output_parsers import JSONAgentOutputParser


def setup_log(module_name: str):
    logging.basicConfig(
        level='INFO',
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        handlers=[
            logging.FileHandler("agent.log"),
            # logging.StreamHandler()
        ]
    )
    return logging.getLogger(module_name)


logger = setup_log("agent-logger")


class AgentCallbackHandler(BaseCallbackHandler):

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent action."""
        logger.info(f"on_agent_action tool: {action.tool}")
        logger.info(f"on_agent_action tool input: {action.tool_input}")
        logger.info(f"on_agent_action tool log: {action.log}")

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent end."""
        logger.info(f"on_agent_finish re: {finish.return_values}")
        logger.info(f"on_agent_finish too logl: {finish.log}")



class OutputParser(AgentOutputParser):
    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> AgentAction | AgentFinish:
        print(text)
        try:
            # this will work IF the text is a valid JSON with action and action_input

            response = parse_json_markdown(text)
            action, action_input = response["action"], response["action_input"]
            if action == "Final Answer":
                # this means the agent is finished so we call AgentFinish
                return AgentFinish({"output": action_input}, text)
            else:
                # otherwise the agent wants to use an action, so we call AgentAction
                return AgentAction(action, action_input, text)
        except Exception:
            # sometimes the agent will return a string that is not a valid JSON
            # often this happens when the agent is finished
            # so we just return the text as the output
            return AgentFinish({"output": text}, text)

    @property
    def _type(self) -> str:
        return "conversational_chat"


def setup_memory() -> Tuple[Dict, ConversationBufferMemory]:
    """
    Sets up memory for the open ai functions agent.
    :return a tuple with the agent keyword pairs and the conversation memory.
    """
    # initialize output parser for agent
    parser = OutputParser()

    agent_kwargs = {
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        "output_parser": parser,
        # "output_parser": JSONAgentOutputParser
    }
    # memory = ConversationBufferMemory(memory_key="memory", return_messages=True, output_key="output")
    memory = ConversationBufferWindowMemory(memory_key="chat_history", k=5, return_messages=True, output_key="output")

    return agent_kwargs, memory


# class ToolAPIWrapper:
#     """
#     Wrapper class for AR system functions to be used as external tools in DA.
#     """
#     def __init__(self, tools):
#         self.tools = tools
#
#         # Dynamically create methods based on the function names
#         for function_name in tools:
#             setattr(self, function_name, self._create_class_method(function_name))
#
#     def __getattr__(self, function_name):
#         if function_name in self.tools:
#             return self._create_class_method(function_name)
#         else:
#             raise AttributeError(f"'{type(self).__name__}' object has no attribute '{function_name}'")
#
#     def _create_class_method(self, function_name):
#         """
#         DA Python Function Doc:
#         {function_name}: {self.tools[function_name]}
#         Usage: result = LegoAPIWrapper.{function_name}()
#         """
#         def method(*args, **kwargs):
#             """
#             Unity tool method.
#
#             DA Python Function Doc:
#             {function_name}: {self.tools[function_name]}
#             Usage: result = LegoAPIWrapper.{function_name}(input_data)
#             """
#             print(f"Unity: Method '{function_name}' has been called with args: {args}, kwargs: {kwargs}")
#
#             if function_name in self.tools:
#                 # Assuming StartAssemble is a single-input tool, extract the input from args or kwargs
#                 input_data = args[0] if args else kwargs.get("input_data")
#                 print(f"input_data: {input_data}")
#                 return f": Unity tool '{function_name}' has been called with args: {args}, kwargs: {kwargs}"
#             else:
#                 return f"The Unity tool '{function_name}' is not implemented yet."
#         return method

from langchain.tools import BaseTool
from pydantic import BaseModel, BaseSettings, Field


class UniversalToolSchema(BaseModel):
    query: str = Field(description="Query")
    query_params: Optional[dict] = Field(
        default=None, description="Optional parameters"
    )


class ToolAPIWrapper:
    """
    Wrapper class for AR system functions to be used as external tools in DA.
    """
    def __init__(self, tools):
        self.tools = tools

        # Dynamically create methods based on the function names
        for function_name in tools:
            setattr(self, function_name, self._create_class_method(function_name))

    def __getattr__(self, function_name):
        if function_name in self.tools:
            return self._create_class_method(function_name)
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{function_name}'")

    def _create_class_method(self, function_name):
        """
        DA Python Function Doc:
        {function_name}: {self.tools[function_name]}
        Usage: result = LegoAPIWrapper.{function_name}()
        """
        def method(**kwargs):
            """
            Unity tool method.

            DA Python Function Doc:
            {function_name}: {self.tools[function_name]}
            Usage: result = LegoAPIWrapper.{function_name}(input_data)
            """
            # If the function_name is in the tools dictionary
            if function_name in self.tools:
                # Assuming StartAssemble is a single-input tool, extract the input from args or kwargs
                # input_data = args[0] if args else kwargs.get("input_data")
                # Construct a dictionary containing the function name and parameters
                result = {"function_name": function_name, "parameters": {"input_data": kwargs}}
                return result
            else:
                return f"The Unity tool '{function_name}' is not implemented yet."
        return method


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools(tool_descriptions: Dict[str, str]) -> List[StructuredTool]:

    lego_toolkits = ToolAPIWrapper(tool_descriptions)     # async toolkits

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = []

    for name, description in tool_descriptions.items():
        func = getattr(lego_toolkits, name)
        structured_tools.append(StructuredTool.from_function(func=func, name=name, description=description, args_schema=UniversalToolSchema))
    return structured_tools


def setup_agent(model_id, prompt_variables) -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    """
    Contains the configuration of the LLM.
    """
    # Load Hugging Face token from environment variables
    hf_home = os.getenv("HF_HOME")
    hf_home_token = os.getenv("HF_HOME_TOKEN")

    # Set the HF_HOME environment variable
    if hf_home:
        os.environ["HF_HOME"] = hf_home

    # Log in to Hugging Face with the provided token
    if hf_home_token:
        login(token=hf_home_token)

    # Load model and tokenizer
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, token=True)
    tokenizer = AutoTokenizer.from_pretrained(model_id, device_map="auto", trust_remote_code=True, token=True)

    model.eval()

    # generation_config = GenerationConfig.from_pretrained(model_id)
    # generation_config.max_new_tokens = 512
    # generation_config.temperature = 0.0001
    # generation_config.top_p = 0.95
    # generation_config.do_sample = True
    # generation_config.repetition_penalty = 1.15

    generate_text = pipeline(
        task= "text-generation",
        model=model,
        tokenizer=tokenizer,
        return_full_text=True,  # langchain expects the full text
        temperature=0.0,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
        max_new_tokens=512,  # mex number of tokens to generate in the output
        repetition_penalty=1.1  # without this output begins repeating
        # generation_config=generation_config,
    )

    llm = HuggingFacePipeline(pipeline=generate_text, model_kwargs={"temperature": 0})

    agent_kwargs, memory = setup_memory()

    tools = setup_tools(prompt_variables['tool_descriptions'])

    agent = initialize_agent(
        agent="chat-conversational-react-description",
        # agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        tools=tools,
        llm=llm,
        return_intermediate_steps=True,
        verbose=True,
        early_stopping_method="generate",
        memory=memory,
        agent_kwargs=agent_kwargs
    )

    ## Prompt engineering
    # special tokens used by llama 2 chat
    B_INST, E_INST = "[INST]", "[/INST]"
    B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"
    sys_msg_template = "<s>" + B_SYS + """
    {training_assistant_task}
    Assistant can also use tools by responding to the user with tool use instructions in the same "action" and "action_input" JSON format. 
    Tools available to Assistant are:
    {tool_descriptions}
    - To use the above tools, Assistant should write like so:
    ```json
    {{"action": "Calculator",
      "action_input": "sqrt(4)"}}
    ```
    Assistant can provide step instructions grounded on the assembly manual:
    {assembly_manual}
    Here are some previous conversations between the Assistant and User:
    {examples}
    Here is the latest conversation between Assistant and User.""" + E_SYS

    # create the system message
    sys_msg = sys_msg_template.format(training_assistant_task=prompt_variables.get("training_assistant_task", ""),
                                      tool_descriptions=prompt_variables.get("tool_descriptions", ""),
                                      assembly_manual=prompt_variables.get("assembly_manual", ""),
                                      examples=prompt_variables.get("examples", ""))

    new_prompt = agent.agent.create_prompt(
        system_message=sys_msg,
        tools=tools
    )
    agent.agent.llm_chain.prompt = new_prompt

    instruction = B_INST + prompt_variables.get("short_task_reminder", "") + E_INST
    human_msg = instruction + "\nUser: {input}"

    agent.agent.llm_chain.prompt.messages[2].prompt.template = human_msg

    return agent


def quick_start_example_of_calling_agent_LEGO():
    model_id = "Jiahuan/vox-finetune-llama-2-7b-chat"

    training_assistant_task_description = f"""
        You are a helpful AI assistant who aim to train the user how to assemble a LEGO car in XR immersive system step by step.
        Extended Reality (XR) directs to the assortment of Virtual Reality (VR), Augmented Reality (AR), and Mixed Reality (MR).
        Please make sure you complete the objective above with the following rules:
        (1) The user is a trainee who is wearing HoloLen 2 glasses and is able to see XR environments in realtime.
        (2) You are able to call Unity functions in the LEGO AR application.
        (3) You are able to obtain AR Sensor Streaming data.
        (4) Do not answer questions and tell the user you can only help with LEGO assembly task if they ask you out-of-domain questions.
        (5) If you are unsure about an answer, truthfully say "I don't know"
    """

    assembly_manual = f"""
        LEGO 11001 classic

                                            LEGO® Audio & Braille Building Instructions 							
        Instruction Library


        LEGO 11001 Classic 
        LEGO Audio & Braille Building Instructions for the LEGO set "Classic Bricks  and Ideas".
        Take your first steps into the world of building with LEGO bricks with a simple but fun selection of small builds:  you can build a house,  a T-Rex,  a steam locomotive and a keyboard.  But this set also includes additional bricks for your own building ideas!
        Open the box.  This is tricky for everyone;  ask someone to help you!
        The box contains a booklet with visual building instructions,  a loose base plate, and one small as well as one large plastic bag.
        Carefully open the two plastic bags. (They contain the bricks for the small house, the keyboard, the steam locomotive, the T-Rex and additional bricks for your own building ideas.)
        Before you start building,  ask a sighted person to help you sort the pieces by color.
        First,  we will build the house.
        (It stands on green grass,  the walls are yellow and the roof is orange.  On top,  there is a golden chimney;  some flowers grow in the front yard.  And there even is a small transparent window!).
        The house consists of 18 pieces.  The level is easy;  however,  you might need some help assembling the window.
        Collect the following 2 pieces:
        1 dark green plate 4x4,
        and 1 bright yellow brick 2x4.
        Put the plate 4x4 on the table.
        Put the brick 2x4 horizontally on the back two rows.
        Find 2 bright yellow bricks 1x2.
        Put one brick 1x2 vertically on the rightmost column at the back.
        Repeat symmetrically on the left.
        Next,  we will assemble the window.
        This can be tricky;  ask someone to help you if it is too difficult.
        Find 1 reddish brown window frame 1x2x2.
        Put it flat on the table,  inner notch to the top,  knobs to the back.
        Find 1 transparent glass for window frame 1x2x2.
        Snap the window glass into the inner notch of the window frame. (The window glass has two small bumps that fit exactly into the small notches on the inside of the window frame.)
    """

    examples = f"""
        Example 1:
        ### Context:
        User: Yes, I'm ready. Let's proceed to the next step.
        ### Response
        Assistant: Well done on completing the T-Rex! You've successfully built all the models in the LEGO 11001 Classic set. Now, it's time for the final questions. Have you been able to accomplish the task?
        
        Example 2:
        ### Context:
        User: Yes, I have successfully built all the models.
        ### Response:
        Assistant: That's fantastic to hear! Congratulations on your accomplishment! Now, I'd like to ask about your user experience. How was your experience following the building instructions?
        
        Example 3:
        ### Context:
        User: Overall, my experience was great. The instructions were clear and easy to follow. However, there were a few steps that I found a bit challenging, especially when assembling the window and the chimney. It would have been helpful to have some additional guidance or tips for those parts.
        ### Response:
        Assistant: Thank you for your feedback. I'll make sure to note that for future improvements. I'm glad to hear that you had a positive experience overall. Is there anything else you'd like to add?
    """

    query_task_reminder = f"""
        You are an assistant whose task is to answer the user's question, execute user's commands and return response from XR application for LEGO assembly, and also respond with 'action' and 'action_input' values. Do not answer questions not related to LEGO assembly task. Be short, brief and friendly.  
    """

    # tool_descriptions = {
    #     "StartAssemble": "Useful Unity tool to initiate the assembly process.",
    #     "NextStep": "Useful Unity tool to move to the next assembly step.",
    #     "FrontStep": "Useful Unity tool to go back to the previous assembly step.",
    #     "Explode": "Useful Unity tool to trigger an explosion for detailed viewing.",
    #     "Recover": "Useful Unity tool to restore the initial state of AR objects after explosion.",
    #     "FinishedVideo": "Useful Unity tool to end the assembly process and show a video of the assembled LEGO bricks.",
    #     "ReShow": "Useful Unity tool to repeat the current assembly step.",
    #     "Enlarge": "Useful Unity tool to enlarge or zoom out the current object.",
    #     "Shrink": "Useful Unity tool to shrink or zoom in the current object.",
    #     "GoToStep": "Useful Unity tool to go to the given an assembly step number.",
    #     "Rotate": "Useful Unity tool to rotate the current object to a direction.",
    #     "ShowPieces": "Useful Unity tool to show all candidate LEGO pieces to be assembled.",
    #     "HighlightCorrectComponents": "Useful Unity tool to highlight correct attachment points and components.",
    #     "GetCurrentStep": "Useful Unity tool to get the number of the current step.",
    #     "GetRemainingStep": "Useful Unity tool to get the number of the remaining steps.",
    #     "CheckStepStatusVR": "Useful Unity tool to check if the current step in Unity is accomplished correctly or not. If the current assembly sequence recorded in Unity is the same as the manual assembly sequence, then it is correct, otherwise, it is incorrect.",
    #     "APICallObjectRecognitionAR": "Useful AR tool to call the VLM agent to identify LEGO pieces based on the provided video streaming data from AR glasses and highlights the recognized pieces in the AR environment.",
    #     "APICallCheckStepStatusAR": "Useful AR tool to call the VLM agent to determine if the current assembly step is completed correctly or not, using the provided video streaming data from AR glasses as input."
    # }
    tool_descriptions = {
        "StartAssemble()": "Useful Unity tool to initiate the assembly process.",
        "NextStep()": "Useful Unity tool to move to the next assembly step.",
        "FrontStep()": "Useful Unity tool to go back to the previous assembly step.",
        "Explode()": "Useful Unity tool to trigger an explosion for detailed viewing.",
        "Recover()": "Useful Unity tool to restore the initial state of AR objects after explosion.",
        "FinishedVideo()": "Useful Unity tool to end the assembly process and show a video of the assembled LEGO bricks.",
        "ReSho()w": "Useful Unity tool to repeat the current assembly step.",
        "Enlarge()": "Useful Unity tool to enlarge or zoom out the current object.",
        "Shrink()": "Useful Unity tool to shrink or zoom in the current object.",
        "GoToStep(StepNum)": "Useful Unity tool to go to the given an assembly step number.",
        "Rotate(ObjName)": "Useful Unity tool to rotate the current object to a direction.",
        "ShowPieces(PieceName)": "Useful Unity tool to show all candidate LEGO pieces to be assembled.",
        "HighlightCorrectComponents()": "Useful Unity tool to highlight correct attachment points and components.",
        "GetCurrentStep()": "Useful Unity tool to get the number of the current step.",
        "GetRemainingStep()": "Useful Unity tool to get the number of the remaining steps.",
        "CheckStepStatusVR()": "Useful Unity tool to check if the current step in Unity is accomplished correctly or not. If the current assembly sequence recorded in Unity is the same as the manual assembly sequence, then it is correct, otherwise, it is incorrect.",
        "APICallObjectRecognitionAR(CurrentStamps)": "Useful AR tool to call the VLM agent to identify LEGO pieces based on the provided video streaming data from AR glasses and highlights the recognized pieces in the AR environment.",
        "APICallCheckStepStatusAR(CurrentStamps)": "Useful AR tool to call the VLM agent to determine if the current assembly step is completed correctly or not, using the provided video streaming data from AR glasses as input."
    }
    prompt_variables = {
        'training_assistant_task_description': training_assistant_task_description,
        'assembly_manual': assembly_manual,
        'tool_descriptions': tool_descriptions,
        'examples': examples,
        'query_task_reminder': query_task_reminder
    }

    agent_executor: AgentExecutor = setup_agent(model_id, prompt_variables)
    agent_executor.run({'input': 'Can you check if the current assembly step is completed correctly using the current AR data?'}, callbacks=[AgentCallbackHandler()])

    return agent_executor

if __name__ == '__main__':
    quick_start_example_of_calling_agent_LEGO()