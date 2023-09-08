from torch import cuda, bfloat16
import transformers
from transformers import LlamaForCausalLM, LlamaTokenizer

# model_id = 'meta-llama/Llama-2-70b-chat-hf'
model_id = 'meta-llama/Llama-2-7b-chat'
model_dir = '/media/PampusData/jpei/transformer_data/llama-2-7b-chat'
# tokenizer = LlamaTokenizer.from_pretrained(model_dir)
# model = LlamaForCausalLM.from_pretrained(model_dir)

device = f'cuda:{cuda.current_device()}' if cuda.is_available() else 'cpu'

# set quantization configuration to load large model with less GPU memory
# this requires the `bitsandbytes` library
bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16
)

# begin initializing HF items, need auth token for these
# hf_auth = '<YOUR_API_KEY>'
model_config = transformers.AutoConfig.from_pretrained(
    model_dir,
    # use_auth_token=hf_auth
)

model = transformers.AutoModelForCausalLM.from_pretrained(
    model_dir,
    trust_remote_code=True,
    config=model_config,
    quantization_config=bnb_config,
    device_map='auto',
    # use_auth_token=hf_auth
)
model.eval()
print(f"Model loaded on {device}")
tokenizer = transformers.AutoTokenizer.from_pretrained(
    model_dir,
    # use_auth_token=hf_auth
)

generate_text = transformers.pipeline(
    model=model, tokenizer=tokenizer,
    return_full_text=True,  # langchain expects the full text
    task='text-generation',
    # we pass model parameters here too
    temperature=0.0,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
    max_new_tokens=512,  # mex number of tokens to generate in the output
    repetition_penalty=1.1  # without this output begins repeating
)

res = generate_text("Explain to me the difference between nuclear fission and fusion.")
print(res[0]["generated_text"])

from langchain.llms import HuggingFacePipeline

llm = HuggingFacePipeline(pipeline=generate_text)

llm(prompt="Explain to me the difference between nuclear fission and fusion.")

from langchain.memory import ConversationBufferWindowMemory
from langchain.agents import load_tools

memory = ConversationBufferWindowMemory(
    memory_key="chat_history", k=5, return_messages=True, output_key="output"
)
tools = load_tools(["llm-math"], llm=llm)