# 1. Introduction
We release the source code for the paper "Autonomous Workflow for Multimodal Fine-Grained Training Assistants Towards Mixed Reality" based on [LangChain](https://github.com/langchain-ai/langchain) framework. 
There are three key phrases as follows:
- Phase 1: Develop the workflow using general LLMs (such as "gpt-3.5-turbo-16k-0613"). See code in [LEGO_data_simulation](LEGO_data_simulation)
- Phase 2: Create XRTA dataset by asking trainees to play with the assistant using the workflow. See code in [LEGO_manual_crawler](LEGO_manual_crawler) and [LEGO_data_simulation](LEGO_data_simulation).
- Phase 3: Finetune LLMs (such as llama2) and replace them in the workflow. 

We release our [dataset](https://osf.io/download/2x5yq/) for open science.

[//]: # (- [godel]&#40;https://github.com/microsoft/GODEL&#41;)

# 2. Setup
Create a virtual environment and install basic requirements.
```bash
conda create -n vox
source activate vox
pip install requirements.txt
```

## Lang Chain 
Install LangChain([repo](https://github.com/langchain-ai/langchain), [doc](https://python.langchain.com/docs/get_started/introduction)) and the required dependencies.
```bash
pip install langchain[all]
pip install openai
```
Set up the keys in a `.env` file in the root directory of the project. Inside the file, add environment variables such as your OpenAI API key ([apply](https://openai.com/blog/openai-api)):

```file
OPENAI_API_KEY="your_api_key_here"
```
Save the file and close it. In your Python script or Jupyter notebook, load the .env file using the following code:
```file
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
```
# 3. Quick start

## 3.1 Dataset creation
```shell
# Crawl LEGO manuals
python LEGO_manual_crawler/lego_audio_instruction_crawler.py
# Generate conversations by running
LEGO_data_simulation/obtain_conversation_from_openai.ipynb
```

## 3.2 Workflow running
### Option 1: Running an interactive demo
```shell
cd ./LEGO_dialogue_agent_openai
python agent_cli.py
```
### Option 2: Create a beautiful web app by streamlit
```bash
streamlit run agent_streamlit.py --server.port 8080
```

# 3. Implementation details
We chose a toy LEGO AR system as an example to show how this workflow functions for XRTA use case.
The XR system can be more complex and practical such as [HOLO](https://holo-light.com/) systems.

We implement a toolkit (a set of APIs / interfaces) to call the services or functions (as in the table) provided by the AR system for LLMs to plan which and when to use.
(See more implementation details at [lego_api_wrapper.py](tools_wrappers/lego_api_wrapper_da_request.py))

We develop API services ([agent_server.py](agent_server.py)) that can be called by the AR application. 
