# 1. Introduction
We develop an Augmented Reality Training Assistant (ARTA) workflow based on [LangChain](https://github.com/langchain-ai/langchain) framework, enlighten by the state-of-the-art [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/). 
In this work, we aim to introduce Large Language Models (LLMs) as human-like "brain" to augment Argument Reality (AR) system with artificial Intelligence; 
and vice versa, we enable Argument Reality (AR) system to provide services by external API tools to augment general LLMs specifically for the ARTA use case, so that AR system can better plan which tool to use and when to use based on fully understanding users' need.
Therefore, there are three key phrase as follows:
- Phase 1: Develop the workflow using general LLMs (such as "gpt-3.5-turbo-16k-0613"). See code in [LEGO_dialogue_agent_openai](LEGO_dialogue_agent_openai)
- Phase 2: Create ARTA dataset by asking trainees to play with assistant using the workflow.
- Phase 3: Finetune LLMs (such as llama2) and replace it in the workflow. See code in [LEGO_dialogue_agent_llama2](LEGO_dialogue_agent_llama2)

![workflow](./image/ARTA-LEGO-workflow.png)

[//]: # (## 2.1 LangChain&#40;[repo]&#40;https://github.com/langchain-ai/langchain&#41;, [doc]&#40;https://python.langchain.com/docs/get_started/introduction&#41;&#41;)

[//]: # (## 2.2 Llama-2 &#40;[repo]&#40;https://github.com/facebookresearch/llama&#41;, [doc]&#40;https://huggingface.co/docs/transformers/main/model_doc/llama2&#41;&#41; + **Toolformer** &#40;[repo]&#40;https://github.com/lucidrains/toolformer-pytorch&#41;&#41; )

[//]: # (In ToolFormer, you pre-train the LLM with examples, so it can, by itself, figure out what APIs are useful for what data. In other words, by teaching it to convert a statement like Two + Three = Five to Two + Three = Calculator&#40;2+3&#41;, you teach it to respond to Two + Three =  with Calculator&#40;2+3&#41;. And then we code up the Calculator API to get the answer, Five and the LLM continues from there [1]&#40;https://www.jezer0x.com/using-external-apis-to-augment-llms/&#41;.)



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

[//]: # (## 2.2 Llama-2 + toolformer)

[//]: # (Download and install llama2.)

[//]: # (```bash)

[//]: # (git clone https://github.com/facebookresearch/llama.git)

[//]: # (cd llama)

[//]: # (pip install -e .)

[//]: # (pip install toolformer-pytorch)

[//]: # (```)

[//]: # ()
[//]: # (Convert to the model at [Huggingface]&#40;https://huggingface.co/&#41;.)

[//]: # (```bash)

[//]: # (# $DATA_DIR='/media/PampusData/jpei')

[//]: # (# source )

[//]: # (python vox_llama2/convert_llama_weights_to_hf.py --input_dir $DATA_DIR/llama_data --model_size 7B --output_dir $DATA_DIR/transformer_data/llama-2-7b-chat)

[//]: # (```)

# 3. Qucik start
### Option 1: Running an interactive demo
```shell
cd ./LEGO_dialogue_agent_openai
python agent_cli.py
```

### Option 2: Create a beautiful web app by streamlit
```bash
streamlit run agent_streamlit.py --server.port 8080
```

# 4. Implementation details
We choose a toy LEGO AR system, namely [BrickDream](https://github.com/kukeya/2023-SWContest/tree/main) , as an example to show how this workflow functions for ARTA use case.
The AR system can be more complex and practical ones such as [HOLO](https://holo-light.com/) systems.

## 4.1 Equip DA with APIWrapper to call customized AR tools
We implement a toolkit (a set of APIs / interfaces) to call the services or functions (as in table) provided by the AR system for LLMs to plan which and when to use.
(See more implementation details at [lego_api_wrapper.py](LEGO_dialogue_agent_openai%2Ftools_wrappers%2Flego_api_wrapper.py))

### 4.1.1 Description of AR functions
| No | Tool Name                    | Description                                                                                                          |
|----|------------------------------|----------------------------------------------------------------------------------------------------------------------|
| 1  | StartAssemble                | Initiates the assembly process.                                                                                      |
| 2  | NextStep                     | Moves to the next assembly step.                                                                                     |
| 3  | FrontStep                    | Goes back to the previous assembly step.                                                                            |
| 4  | Explode                      | Triggers an explosion for detailed viewing.                                                                         |
| 5  | Recover                      | Restores the initial state of AR objects after an explosion.                                                         |
| 6  | FinishedVideo                | Ends the assembly process and shows a video of the assembled LEGO bricks.                                            |
| 7  | ReShow                       | Repeats the current assembly step.                                                                                  |
| 8  | Enlarge                      | Enlarges or zooms out the current object.                                                                           |
| 9  | Shrink                       | Shrinks or zooms in the current object.                                                                             |
| 10 | GoToStep                     | Goes to the given assembly step number.                                                                             |
| 11 | Rotate                       | Rotates the current object to a direction.                                                                         |
| 12 | ShowPieces                   | Shows all candidate LEGO pieces to be assembled.                                                                   |
| 13 | HighlightCorrectComponents   | Highlights correct attachment points and components.                                                               |
| 14 | GetCurrentStep               | Gets the number of the current step.                                                                                |
| 15 | GetRemainingStep             | Gets the number of the remaining steps.                                                                            |
| 16 | CheckStepStatusVR            | Checks if the current step in Unity is accomplished correctly or not. |
| 17 | APICallObjectRecognitionAR   | Calls the VLM agent to identify LEGO pieces based on the provided video streaming data from AR glasses and highlights the recognized pieces in the AR environment. |
| 18 | APICallCheckStepStatusAR     | Calls the VLM agent to determine if the current assembly step is completed correctly or not, using the provided video streaming data from AR glasses as input. |
                            |

### 4.1.2 Responses from AR functions
To make the real-time interaction between AR application and DA. 
The real implementation is in Unity (C#), however, to easily debug, we created a python simulated client and first run it.
```shell
# cd LEGO_dialogue_agent_openai/tools_wrappers
python lego_streamlit.py
```
Then we test if we can get the correct response from the simulated client.
```shell
python lego_streamlit.py
```

## 4.2 Develop DA's API service
We develop API services  ([agent_lego_api.py](LEGO_dialogue_agent_openai%2Fagent_lego_api.py)) that can be called by AR application (such as BrickDream). 
- ``citl`` ([Websocket](https://github.com/jina-ai/langchain-serve/blob/main/examples/websockets/hitl/README.md))
- ``ask`` ([REST APIs](https://github.com/jina-ai/langchain-serve/blob/main/examples/rest/README.md))

> When to Choose Sockets:
> - Use sockets when you need low-latency, real-time, or continuous communication.
> - For scenarios like online games, chat applications, live streaming, or any application where rapid data transfer is crucial.
> - When full-duplex communication is essential, and you want to maintain an open connection.
> 
> When to Choose RESTful API:
> - Use RESTful APIs when you need a simple and web-friendly way to exchange data between applications.
> - If you want to create an HTTP-based API that other services or clients can access.
> - When real-time, low-latency communication is not a strict requirement.

### Step 1: Refactor your code to function(s) that should be served with @serving decorator
```shell
# Decorate the function with the @serving decorator for WebSocket communication
@serving(websocket=True)
async def citl(query: str, **kwargs) -> str:
    """
    Client in the loop
    """
    # auth_response = kwargs['auth_response']  # This will be 'userid'
    agent_executor: AgentExecutor = setup_agent_citl(**kwargs)
    try:
        # response = agent_executor.run(query)
        response = agent_executor.run(query, callbacks=[AgentCallbackHandler()])
        print(get_colored_text("Response: >>> ", "green"))
        print(get_colored_text(response, "green"))
    except Exception as e:
        print(get_colored_text(f"Failed to process {query}", "red"))
        print(get_colored_text(f"Error {e}", "red"))
    return response
```

### Step 2: Create a `requirements.txt` file in your app directory ([LEGO_dialogue_agent_openai](LEGO_dialogue_agent_openai)) to ensure all necessary dependencies are installed


### Step 3: Run lc-serve deploy local app to test your API locally
First, start the server.
```shell
lc-serve deploy local agent_lego_api
```
Note that **agent_lego_api** is the name of the module ([agent_lego_api.py](LEGO_dialogue_agent_openai%2Fagent_lego_api.py)) that contains the `citl` function.

Second, test `citl` sync api by the simulated client request ([lego_app_simulated_client_request.py](LEGO_dialogue_agent_openai%2Ftools_wrappers%2Flego_app_simulated_client_request.py)). 
In practice, the request is from the AR application (C# in Unity).

(Optional) test `ask` API with a customized input as an input with a cURL command.
```shell input
curl -X 'POST' \
  'http://localhost:8080/ask' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Can you start to teach me how to assemble a LEGO car?",
  "envs": {
    "OPENAI_API_KEY": "'"${OPENAI_API_KEY}"'"
  }
}'
```
Then you will see output like this:
```shell output
{
  "result": "Of course! I can guide you through the process of assembling a LEGO car. Let's get started!\n\nStep 1:...",
  "error": "",
  "stdout": " Entering Chain run with input:\n\u001b[0m{\n  \"input\": \"Can you start to teach me how to assemble a LEGO car?\",\n  \"memory\": []\n}\n\u001b[32;1m\u001b[1;3m[llm/start]\u001b[0m \u001b[1m[1:chain:AgentExecutor > 2:llm:ChatOpenAI] Entering LLM run with input:\n\u001b[0m{\n  \"prompts\": [\n    \"System: You are a helpful AI assistant.\\nHuman: Can you start to teach me how to assemble a LEGO car?"
}
```

- `POST /ask` is generated from ask function defined in agent_cli.py.
- `query` is an argrment defined in `ask` function.
- `envs` is a dictionary of environment variables that will be passed to all the functions decorated with `@serving` decorator.
- return type of `ask` function is `str`. So, `result` would carry the return `value` of ask function.
- If there is an error, `error` would carry the error message.
- `stdout` would carry the output of the function decorated with `@serving` decorator.

### Step 4: Run lc-serve deploy jcloud app to deploy your API to Jina AI Cloud
Then your service can be in practical use now.
```shell
# Login to Jina AI Cloud
jina auth login

# Deploy your app to Jina AI Cloud
lc-serve deploy jcloud agent_lego_api --secrets .env
```

## 4.3 Agent Loop
![openai-agent-loop.jpg](image%2Fopenai-agent-loop.jpg)
## 4.4 LEGO ARTA Deployment
![ARTA-LEGO-deployment.jpg](image%2FARTA-LEGO-deployment.jpg)

```shell
# kill the port sometimes
npx kill-port --port 8080
```

## Reference
[1] LangChain Chat with Custom Tools, Functions and Memory [[blog]](https://medium.com/@gil.fernandes/langchain-chat-with-custom-tools-functions-and-memory-e34daa331aa7)
[[repo]](https://github.com/gilfernandes/chat_functions)

[2] BrickDream [[repo]](https://github.com/kukeya/2023-SWContest/tree/main)

ln -s /media/Blue2TB3/jpei/cache-huggingface/ huggingface