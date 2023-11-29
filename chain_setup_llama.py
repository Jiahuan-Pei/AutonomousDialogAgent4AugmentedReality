import os
from typing import Tuple, Dict, List

from langchain.agents import initialize_agent
from langchain.tools import StructuredTool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts.chat import MessagesPlaceholder
from langchain.llms import HuggingFacePipeline

from langchain.chains import LLMChain

from langchain.prompts import ChatPromptTemplate
from langchain.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain.schema.messages import SystemMessage

from langchain.callbacks.manager import CallbackManager
import tools_wrappers
import asyncio
from langchain.callbacks.streaming_stdout_final_only import (
    FinalStreamingStdOutCallbackHandler,
)


class Config:
    """
    Contains the configuration of the LLM.
    """
    import transformers
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftConfig

    project = "vox-finetune"
    base_model_name = "llama-2-7b-chat"
    storage_dir = '/media/PampusData/jpei'
    data_name = 'testdata'
    checkpoint_name = 'checkpoint-500'
    # base_model_id = "meta-llama/Llama-2-7b-hf"
    base_model_id = f'{storage_dir}/transformer_data/{base_model_name}'  # local model dir: /media/PampusData/jpei/transformer_data/llama-2-7b-chat
    run_name = f'{base_model_name}-{data_name}'
    ft_model_id = f'{storage_dir}/{project}/{run_name}'
    ft_ckpt_id = f'{ft_model_id}/{checkpoint_name}'

    config = PeftConfig.from_pretrained(ft_model_id)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    ft_model = AutoModelForCausalLM.from_pretrained(
        config.base_model_name_or_path,
        return_dict=True,
        quantization_config=bnb_config,
        device_map="auto",
        # device_map={"": 'cuda'},
        trust_remote_code=True
    )

    tokenizer = AutoTokenizer.from_pretrained(ft_model_id, add_bos_token=True, trust_remote_code=True)

    generate_text = transformers.pipeline(
        model=ft_model, tokenizer=tokenizer,
        return_full_text=True,  # langchain expects the full text
        task='text-generation',
        # we pass model parameters here too
        temperature=0.0,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
        max_new_tokens=512,  # mex number of tokens to generate in the output
        repetition_penalty=1.1  # without this output begins repeating
    )


def setup_memory() -> Tuple[Dict, ConversationBufferMemory]:
    """
    Sets up memory for the open ai functions agent.
    :return a tuple with the agent keyword pairs and the conversation memory.
    """
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task_instructions/LEGO_Assembly_Task_Instructions.txt')
    LEGO_assembly_task_instructions = open(filename, 'r').read()
    system_message = SystemMessage(
        content=LEGO_assembly_task_instructions
    )
    agent_kwargs = {
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        "system_message": system_message,
    }
    memory = ConversationBufferMemory(memory_key="memory", return_messages=True)

    return agent_kwargs, memory


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools() -> List[StructuredTool]:

    lego_toolkits = tools_wrappers.LegoAPIWrapper()     # async toolkits

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = []

    for name, description in lego_toolkits.descriptions.items():
        func = getattr(lego_toolkits, name)
        structured_tools.append(StructuredTool.from_function(func=func, name=name, description=description))

    return structured_tools


def setup_agent_streaming(**kwargs) -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    # streaming_handler = AsyncCallbackHandler
    llm = ChatOpenAI(
        temperature=cfg.temperature,
        model=cfg.model,
        verbose=cfg.verbose,
        streaming=True,  # ! Important: Pass `streaming=True` to make sure the client receives the data.
        callbacks=[FinalStreamingStdOutCallbackHandler(
            answer_prefix_tokens=['Answer']
        )], # ! Important:
        # callbacks = [FinalStreamingStdOutCallbackHandler()]  # ! Important:
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


def setup_agent() -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    llm = HuggingFacePipeline(pipeline=cfg.generate_text)

    agent_kwargs, memory = setup_memory()

    tools = setup_tools()

    agent = initialize_agent(
        agent="chat-conversational-react-description",
        tools=tools,
        llm=llm,
        verbose=True,
        early_stopping_method="generate",
        memory=memory,
        agent_kwargs=agent_kwargs
        # agent_kwargs={"output_parser": parser}
    )

    return agent
