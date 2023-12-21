"""
Submit:
    nohup python evaluation_agent.py > agent_evaluation.output.log 2>&1 &
    nohup python evaluation_agent.py --model_id Jiahuan/voxreality-arta-llama2-7b-chat-v3 > agent_finetune_teach_edh_evaluation.output.log 2>&1 &
Check:
    ps aux | grep "evaluation.py"
    watch -n 1 nvidia-smi
GPU Usage:
    17GiB / 24GiB
"""
import os.path
import json
from tqdm import tqdm
import numpy as np
import torch
import transformers
from datasets import load_dataset
import evaluate
from langchain.llms import HuggingFacePipeline
import argparse
from transformers import AutoTokenizer

import os
from typing import Tuple, Dict, List

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from transformers import GenerationConfig, pipeline
from huggingface_hub import login

from utils import Config, formatting_func_inference

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

from agent_logger import AgentCallbackHandler
from pydantic import BaseModel, Field

tool_descriptions = {
    "Stop": "This tool allows users to bring any ongoing movement or action to an immediate halt, providing a quick and effective way to pause virtual interactions.",
    "Moveto": "With this tool, users can designate a specific location within the virtual environment and seamlessly transport themselves to that chosen spot, enhancing navigation efficiency.",
    "Forward": "Initiates forward movement, allowing users to explore the virtual space in the direction they are facing. The speed and distance may be adjustable based on user preferences.",
    "Backward": "Enables backward movement, providing users with the ability to retreat or reposition within the virtual environment. The speed and distance can be customized for a personalized experience.",
    "TurnLeft": "This tool facilitates a leftward rotation, allowing users to change their orientation in the virtual environment, enhancing situational awareness and exploration.",
    "TurnRight": "Similar to 'Turn Left,' this tool enables a rightward rotation, empowering users to adjust their perspective and navigate seamlessly within the virtual space.",
    "LookUp": "Allows users to gaze upwards in the virtual environment, facilitating a more immersive experience by exploring the details above eye level.",
    "LookDown": "This tool permits users to lower their viewpoint within the virtual environment, offering a comprehensive exploration of details at different levels.",
    "PanLeft": "Enables a smooth horizontal panning motion to the left, enhancing the user's ability to survey their surroundings or focus on specific points of interest.",
    "PanRight": "Similar to 'Pan Left,' this tool initiates a horizontal panning motion to the right, offering users a flexible way to observe their surroundings and interact with virtual elements.",
    "MoveUp": "Allows users to ascend vertically within the virtual environment, providing access to higher platforms or viewpoints for an enhanced interactive experience.",
    "MoveDown": "This tool facilitates a controlled descent within the virtual space, enabling users to explore lower levels or adjust their position as needed.",
    "DoubleForward": "Doubles the speed or distance covered when moving forward, providing a faster means of traversal for users who prefer a more rapid pace.",
    "DoubleBackward": "Similar to 'Double Forward,' this tool increases the speed or distance covered when moving backward, offering a quicker retreat or repositioning option.",
    "Navigation": "Serves as a centralized tool for accessing various movement and exploration commands, streamlining the user's ability to navigate and interact within the virtual environment.",
    "Pickup": "Enables users to grasp and interact with virtual objects, enhancing the sense of presence and allowing for a more immersive and tactile experience.",
    "Place": "Allows users to release or position virtual objects in the desired location within the environment, contributing to a more interactive and dynamic virtual world.",
    "Open": "Initiates the action of opening virtual doors, containers, or other interactive elements within the environment, adding a layer of realism and engagement.",
    "Close": "Similar to 'Open,' this tool facilitates the closure of virtual doors, containers, or interactive elements, providing users with control over their surroundings.",
    "ToggleOn": "Activates a virtual switch or control, turning on specific elements or features within the environment, enhancing user interaction and customization.",
    "ToggleOff": "Functions as a tool to deactivate virtual switches or controls, turning off specific elements or features within the environment, allowing users to manage their virtual space efficiently."
}


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


class TeachAPIWrapper:
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
        def method():
            print(f"Unity: Method '{function_name}' has been called.")
            return f"Response of '{function_name}'"

        return method


from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    action: str = Field()
    action_input: Optional[Dict[str, Any]] = Field(None, alias='json')


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools() -> List[StructuredTool]:
    lego_toolkits = TeachAPIWrapper(tool_descriptions)  # async toolkits

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = []

    for name, description in tool_descriptions.items():
        func = getattr(lego_toolkits, name)
        structured_tools.append(
            StructuredTool.from_function(func=func, name=name, description=description))
    return structured_tools


def setup_agent() -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    # Model
    # Load model directly
    model_id = args.model_id

    # Load Hugging Face token from environment variables
    hf_home = os.getenv("HF_HOME")
    hf_home_token = os.getenv("HF_HOME_TOKEN")

    # Set the HF_HOME environment variable
    if hf_home:
        os.environ["HF_HOME"] = hf_home

    # Log in to Hugging Face with the provided token
    if hf_home_token:
        login(token=hf_home_token)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(model_id, device_map="auto", trust_remote_code=True, token=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map="auto",
                                                 trust_remote_code=True, token=True)
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

    llm = HuggingFacePipeline(pipeline=generate_text, model_kwargs={"temperature": 0, "batch_size": 8})

    agent_kwargs, memory = setup_memory()

    tools = setup_tools()

    agent = initialize_agent(
        agent="chat-conversational-react-description",
        # agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        tools=tools,
        llm=llm,
        verbose=True,
        # verbose=False,
        early_stopping_method="generate",
        memory=memory,
        agent_kwargs=agent_kwargs
    )

    # special tokens used by llama 2 chat
    B_INST, E_INST = "[INST]", "[/INST]"
    B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"

    training_assistant_task = f"""
        You are a helpful AI assistant (Driver) who aim to reply the user (Commander) by following the commands to do household in VR immersive system step by step.
    """

    examples = f"""
        Example 1:
        ### Context:
        Driver: Hello. How may I assist today?
        ### Response:
        Commander: hello, we are cooking 2 slices of potato
        
        Example 2:
        ### Context:
        Driver: task? Commander: slice tomato. then clean a bowl. knife is in the fridge Driver: bowl Commander: drawer above microwave Driver: next
        ### Response:
        Commander: that's not the bowl
        
        Example 3:
        ### Context:
        Driver: hi Commander: Hello. Driver: what to do Commander: Today you will boil a potato a potato and water Driver: ok. where is the potato Commander: You can find a potato on the counter to the left of the stove
        ### Response:
        Driver: what next
    """

    short_task_reminder = f"""
        You are an assistant whose task is to answer the user's question, execute user's commands and return response.  
    """

    # create the system message
    sys_msg = "<s>" + B_SYS + f"""
    {training_assistant_task}
    Assistant can also use tools by responding to the user with tool use instructions in the same "action" and "action_input" JSON format. 
    Tools available to Assistant are:
    {tool_descriptions}
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


def fast_compute_metrics(predictions, references):
    """
    :param evaluation_result:
    # Example usage:
    evaluation_results = {
        'input': "Input prompt",
        'prediction': "Generated response",
        'reference': "Reference response",
    }
    :param tokenizer:
    :return:
    """
    bleu = evaluate.load("bleu")  # Measures the similarity between the generated text and reference text based on n-grams.
    rouge = evaluate.load('rouge')  # Evaluates the overlap between the generated text and reference text in terms of n-grams and word sequences.
    meteor = evaluate.load('meteor')  # Considers precision, recall, and harmonized mean of precision and recall with stemming and synonymy matching.

    corpus_metrics = {
        'BLEU': bleu.compute(predictions=predictions, references=[[result] for result in references]),
        'ROUGE': rouge.compute(predictions=predictions, references=references),
        'METOR': meteor.compute(predictions=predictions, references=references),
    }


    return corpus_metrics


def evaluate_main_agent(model_id, dataset_id, output_dir, max_tokens, batch_size):

    test_dataset = load_dataset(dataset_id, split='test', use_auth_token=True)

    agent_executor: AgentExecutor = setup_agent()

    inputs = [example['input'] for example in test_dataset]
    references = [example['output'] for example in test_dataset]
    predictions = []

    for batch_start in tqdm(range(0, len(inputs), batch_size)):
        # batch_model_inputs = [data.to("cuda") for data in inputs[batch_start:batch_start + batch_size]]
        batch_model_inputs = inputs[batch_start:batch_start + batch_size]

        # Create a list of dictionaries with the correct keys
        batch_model_inputs = [{'input': text, 'Stop': '### Response: '} for text in batch_model_inputs]

        batch_generated_responses = agent_executor.batch(batch_model_inputs)

        batch_generated_responses = [t.split('### Response: ')[-1].strip() for t in batch_generated_responses]

        predictions.extend(batch_generated_responses)

        # Monitor GPU memory usage
        current_memory_allocated = torch.cuda.memory_allocated()
        max_memory_allocated = torch.cuda.max_memory_allocated()
        print(f"Current Memory Allocated: {current_memory_allocated / (1024 ** 3):.2f} GB")
        print(f"Max Memory Allocated: {max_memory_allocated / (1024 ** 3):.2f} GB")
        # Empty GPU cache to release memory
        torch.cuda.empty_cache()

    # Compute evaluation metrics
    metrics = fast_compute_metrics(references, predictions)

    evaluation_results = json.dumps(metrics, indent=4)

    print(evaluation_results)

    with open(f'{output_dir}/{model_id.split("/")[-1]}_{dataset_id.split("/")[-1]}_agent_evaluation_results.json', 'w') as json_file:
        json.dump(evaluation_results, json_file, indent=2)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    evaluation_output = [{"input": i, "reference": r, "prediction": p} for (i, r, p) in
                          zip(*[inputs, references, predictions])]

    with open(f'{output_dir}/{model_id.split("/")[-1]}_{dataset_id.split("/")[-1]}_agent_evaluation_output.json', 'w') as json_file:
        json.dump(evaluation_output, json_file, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_id', default='meta-llama/Llama-2-7b-chat-hf', type=str, help='the name or the abstract path of the model')
    parser.add_argument('--dataset_id', default='Jiahuan/teach_edh', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--project_name', default='vox-finetune', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--output_dir', default='/media/Blue2TB3/jpei/evaluation_results', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--cache_dir', default='/media/Blue2TB3/jpei/cache-huggingface-2/datasets', type=str, help='the name or the abstract path of the dataset')
    parser.add_argument('--max_tokens', default=512, type=int, help='max number of tokens')
    parser.add_argument('--batch_size', default=8, type=int, help='batch size')
    args = parser.parse_args()
    evaluate_main_agent(args.model_id, args.dataset_id, args.output_dir, args.max_tokens, args.batch_size)
