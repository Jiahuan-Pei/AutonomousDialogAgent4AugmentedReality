import os
import time
from typing import Tuple, Dict, List

from langchain.agents import initialize_agent
from langchain.tools import StructuredTool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts.chat import MessagesPlaceholder
from langchain.schema.messages import SystemMessage
from callbacks import AgentCallbackHandler

task_instruction = f"""
The task it to generate conversations between trainer and trainee grounded on the task-specific guidelines.
The trainer aims to teach the trainee how to accomplish the assembly task based on the task-specific guidelines, supported by an XR application.
Specifically, the trainee is wearing AR glasses to see both VR environment and real world.
The trainee knows nothing about the guidelines before trainer's guidance.
For each step,
the trainee must ask at least one deep-dive question, or request a troublesome issue if he or she cannot follow the guide, or call tools from XR application and learn how to use those tools;
the trainer must answer the question, assist the trainee, show them the responses of the execution of the tools.
At the end of a conversation,
first, trainer must ask if the trainee has accomplished the task and the trainee must tell if the trainee can accomplish the task;
second, trainer must ask how is user experience, and the trainee provide feedback on the user experience.
You must add a section title to separate which key point in the guideline in the generated conversation and generate until the final step of the guidelines.
"""

tool_descriptions = {
    "StartAssemble": "Useful Unity tool to initiate the assembly process.",
    "NextStep": "Useful Unity tool to move to the next assembly step.",
    "FrontStep": "Useful Unity tool to go back to the previous assembly step.",
    "Explode": "Useful Unity tool to trigger an explosion for detailed viewing.",
    "Recover": "Useful Unity tool to restore the initial state of AR objects after explosion.",
    "FinishedVideo": "Useful Unity tool to end the assembly process and show a video of the assembled LEGO bricks.",
    "ReShow": "Useful Unity tool to repeat the current assembly step.",
    "Enlarge": "Useful Unity tool to enlarge or zoom out the current object.",
    "Shrink": "Useful Unity tool to shrink or zoom in the current object.",
    "GoToStep": "Useful Unity tool to go to the given an assembly step number.",
    "Rotate": "Useful Unity tool to rotate the current object to a direction.",
    "ShowPieces": "Useful Unity tool to show all candidate LEGO pieces to be assembled.",
    "HighlightCorrectComponents": "Useful Unity tool to highlight correct attachment points and components.",
    "GetCurrentStep": "Useful Unity tool to get the number of the current step.",
    "GetRemainingStep": "Useful Unity tool to get the number of the remaining steps.",
    "CheckStepStatusVR": "Useful Unity tool to check if the current step in Unity is accomplished correctly or not. If the current assembly sequence recorded in Unity is the same as the manual assembly sequence, then it is correct, otherwise, it is incorrect.",
    "APICallObjectRecognitionAR": "Useful AR tool to call the VLM agent to identify LEGO pieces based on the provided video streaming data from AR glasses and highlights the recognized pieces in the AR environment.",
    "APICallCheckStepStatusAR": "Useful AR tool to call the VLM agent to determine if the current assembly step is completed correctly or not, using the provided video streaming data from AR glasses as input."
}

sys_prompt = f"""
### Instruction:
{task_instruction}

You can call the following tools:
{tool_descriptions}

### Examples:
Example 1:
Trainee: Hi, I'm ready to start building the LEGO Creator set "Creator Sunken Treasure Mission". What should I do first?
Trainer: Great! Let's start by opening the box. It might be a bit tricky, so you can ask someone to help you with that.

Example 2:
Trainee: I've added the bricks on top of the angle plates. What's the next step?
Trainer: That completes this step! You've successfully built the stabilizer bars and added the angle plates and bricks. Is there anything you're unsure about or any questions you have?
"""


class Config:
    """
    Contains the configuration of the LLM.
    """
    model = 'gpt-3.5-turbo-16k-0613'
    try:
        OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    except:
        print(f'OPENAI_API_KEY={OPENAI_API_KEY}')
    temperature = 0.0
    verbose = True


class LegoAPIWrapper:
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
        def method():
            print(f"Unity: Method '{function_name}' has been called.")
            return f"Response of '{function_name}'"

        return method


def setup_memory() -> Tuple[Dict, ConversationBufferMemory]:
    """
    Sets up memory for the open ai functions agent.
    :return a tuple with the agent keyword pairs and the conversation memory.
    """
    system_message = SystemMessage(content=f"{sys_prompt}")
    agent_kwargs = {
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        "system_message": system_message,
    }
    memory = ConversationBufferMemory(memory_key="memory", return_messages=True)

    return agent_kwargs, memory


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools() -> List[StructuredTool]:
    lego_toolkits = LegoAPIWrapper(tool_descriptions)  # async toolkits

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = []
    # structured_tools = [metadata_retriever]

    for name, description in tool_descriptions.items():
        func = getattr(lego_toolkits, name)
        structured_tools.append(StructuredTool.from_function(func=func, name=name, description=description))

    return structured_tools


def setup_agent() -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    llm = ChatOpenAI(
        temperature=cfg.temperature,
        model=cfg.model,
        verbose=cfg.verbose
    )

    agent_kwargs, memory = setup_memory()

    tools = setup_tools()

    return initialize_agent(
        tools,
        llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=False,
        agent_kwargs=agent_kwargs,
        memory=memory
    )


agent_executor: AgentExecutor = setup_agent()

manual_dir = '/media/Blue2TB3/jpei/vox_arta_dataset/manuals/lego'
import json
import math
from tqdm.notebook import tqdm
from pathlib import Path
import re

count_dialogue = 0
chunk_size = 10
max_words = int(16385 * 0.75)


def generate_conversation_per_file(fname, mdir=manual_dir):
    with open(f'{mdir}/{fname}/{fname}.json', 'r', encoding='utf-8') as fr:
        json_instructions = json.load(fr)['instructions']
        summary = json_instructions[0]['text']
        instructions = [d['text'] for d in json_instructions[1:]]

        ## Chunk the original instructions
        n = math.ceil(len(instructions) / chunk_size)
        for i_chunk in range(n):
            output_file = f'{mdir}/{fname}/{fname}_{i_chunk}.txt'
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print('=' * 10, '> Pass as already exist.')
            else:
                start_index = i_chunk * chunk_size
                end_index = min(i_chunk * chunk_size + chunk_size, len(instructions) - 1)
                chuck_instruction_str = '\n'.join(instructions[start_index:end_index])
                chuck_instruction_str = ' '.join(chuck_instruction_str.split()[:max_words])
                print('*' * 50, fname, f'; Chunk {i_chunk}/{n}',
                      f'; Instruction indexes {start_index + 1}: {end_index}', '*' * 50)
                # print(chuck_instruction_str)

                ## Prepare query prompt
                query_prompt = f"""
                    The task it to generate conversations between trainer and trainee grounded on the task-specific guidelines.
                    ### Guidelines:
                    {summary}
                    {chuck_instruction_str}
                    ### Response:
                """.strip()
                query_prompt = re.sub(r'\s+', ' ', query_prompt)
                query_prompt = re.sub(r'\n+', '\n', query_prompt)
                # print('-'*50, '\n', query_prompt)

                ## Carefully call ChatGPT API as it costs credits!
                response = agent_executor.run(query_prompt, callbacks=[AgentCallbackHandler()])
                with open(output_file, 'w') as fw:
                    fw.write(response)

                time.sleep(60 * 4)


for folder_name in tqdm(os.listdir(manual_dir)):
    if Path(os.path.join(manual_dir, folder_name)).is_dir():
        generate_conversation_per_file(folder_name)
    else:
        print(f'Pass as not a folder {folder_name}')
