import os
from typing import Tuple, Dict, List

from langchain.agents import initialize_agent
from langchain.tools import StructuredTool
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.prompts.chat import MessagesPlaceholder
from langchain.llms import HuggingFacePipeline
from langchain.schema.messages import SystemMessage, HumanMessage

import tools_wrappers
import transformers
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, GenerationConfig, pipeline
from peft import PeftConfig
from datetime import datetime

from langchain.agents import AgentOutputParser, AgentType
from langchain.agents.conversational_chat.prompt import FORMAT_INSTRUCTIONS
from langchain.output_parsers.json import parse_json_markdown
from langchain.schema import AgentAction, AgentFinish

from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.history import FileHistory

from langchain.input import get_colored_text
from callbacks.agent_logger import AgentCallbackHandler

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from transformers import GenerationConfig, pipeline
from langchain.llms import HuggingFacePipeline


class Config:
    """
    Contains the configuration of the LLM.
    """
    # Model
    # Load model directly
    model_id = "Jiahuan/vox-finetune-llama-2-7b-chat"
    # model_id = "/media/PampusData/jpei/transformer_data/llama-2-7b-chat" # Base model
    # model_id = "/media/PampusData/jpei/vox-finetune/llama-2-7b-chat-teach-gpt_teacher-gpt4tools-camel-2023-11-30-22-52"

    # Load model directly

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(model_id, device_map="auto", trust_remote_code=True, use_auth_token=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, use_auth_token=True)
    model.eval()

    generation_config = GenerationConfig.from_pretrained(model_id)
    generation_config.max_new_tokens = 512
    generation_config.temperature = 0.0001
    generation_config.top_p = 0.95
    generation_config.do_sample = True
    generation_config.repetition_penalty = 1.15

    generate_text = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        generation_config=generation_config,
    )


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
        "output_parser": parser
    }
    # memory = ConversationBufferMemory(memory_key="memory", return_messages=True, output_key="output")
    memory = ConversationBufferWindowMemory(memory_key="chat_history", k=5, return_messages=True, output_key="output")

    return agent_kwargs, memory


from pydantic import BaseModel, Field
import json

class LEGOInput(BaseModel):
    question: str = Field()


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools() -> List[StructuredTool]:

    lego_toolkits = tools_wrappers.LegoAPIWrapper()     # async toolkits

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = []

    for name, description in lego_toolkits.descriptions.items():
        func = getattr(lego_toolkits, name)
        structured_tools.append(StructuredTool.from_function(func=func, name=name, description=description, args_schema=LEGOInput))
    return structured_tools


def setup_agent() -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    llm = HuggingFacePipeline(pipeline=cfg.generate_text, model_kwargs={"temperature": 0})

    agent_kwargs, memory = setup_memory()

    tools = setup_tools()

    agent = initialize_agent(
        agent="chat-conversational-react-description",
        # agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        # agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        # agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        tools=tools,
        llm=llm,
        verbose=True,
        early_stopping_method="generate",
        memory=memory,
        agent_kwargs=agent_kwargs
    )

    # special tokens used by llama 2 chat
    B_INST, E_INST = "[INST]", "[/INST]"
    B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"

    training_assistant_task = f"""
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
        The window is finished!  Mount it horizontally in the middle of the second row from the back.
        Find 2 bright yellow bricks 1x2.
        Put one vertically to the right of the window.
        Repeat symmetrically on the left.
        Find 1 bright yellow plate 2x4.
        Put it horizontally on the two back rows.
        Collect the following 3 pieces:
        1 bright yellow brick 2x2,
        and 2 bright orange roof tiles 2x2.
        Put the brick 2x2 on top in the middle of the back two rows.
        Put one roof tile 2x2 to the right,  overhanging to the right,  slide to the right.
        Repeat symmetrically on the left.
        Find 2 bright orange roof tiles 2x2.
        Put one on the right four knobs at the back,  slide to the right.
        Repeat symmetrically on the left.
        Find 1 warm gold small nose cone 1x1.
        Put it on the back knob on the left.
        (This is the chimney of the house!).
        Find 1 dark green small nose cone 1x1.
        Put it on the rightmost knob on the front row of the plate 4x4.
        Find 2 bright purple flowers 1x1.
        Put one on top.
        Put the other one to the left on the plate 4x4.
        The house is finished!  Well done!  Look outside the window  and wave to your neighbors!  And don't forget to water your flowers in the front yard.
    """

    tool_descriptions = f"""
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
    """

    examples = f"""
        User: Yes, I'm ready.
        Assistant: Fantastic! Let's proceed to the next step.
        Assistant: Well done on completing the T-Rex! You've successfully built all the models in the LEGO 11001 Classic set. Now, it's time for the final questions. Have you been able to accomplish the task?
        User: Yes, I have successfully built all the models.
        Assistant: That's fantastic to hear! Congratulations on your accomplishment! Now, I'd like to ask about your user experience. How was your experience following the building instructions?
        User: Overall, my experience was great. The instructions were clear and easy to follow. However, there were a few steps that I found a bit challenging, especially when assembling the window and the chimney. It would have been helpful to have some additional guidance or tips for those parts.
        Assistant: Thank you for your feedback. I'll make sure to note that for future improvements. I'm glad to hear that you had a positive experience overall. Is there anything else you'd like to add?
        User: No, that's all. Thank you for your guidance!
        Assistant: You're welcome! It was my pleasure to assist you. If you have any more questions or need further assistance in the future, feel free to reach out. Happy building!
    """

    short_task_reminder = f"""
        Your task is to answer the user's question, execute user's commands and return response from XR application for LEGO assembly, and also respond with 'action' and 'action_input' values. Do not answer questions not related to LEGO assembly task. Be short, brief and friendly.
    """

    # create the system message
    sys_msg = "<s>" + B_SYS + f"""
    {training_assistant_task}
    Assistant can also use tools by responding to the user with tool use instructions in the same "action" and "action_input" JSON format. 
    Tools available to Assistant are:
    {tool_descriptions}
    Assistant can provide step instructions grounded on the assembly manual:
    {assembly_manual}
    Here are some previous conversations between the Assistant and User:
    {examples}
    Here is the latest conversation between Assistant and User.""" + E_SYS
    new_prompt = agent.agent.create_prompt(
        system_message=sys_msg,
        tools=tools
    )
    agent.agent.llm_chain.prompt = new_prompt

    instruction = B_INST + short_task_reminder + E_INST
    human_msg = instruction + "\nUser: {input}"

    agent.agent.llm_chain.prompt.messages[2].prompt.template = human_msg

    return agent
