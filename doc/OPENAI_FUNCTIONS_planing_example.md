How does the AgentType.OPENAI_FUNCTIONS do planing using LLMs and tools? Here is a quick example.

The general chain of thoughs is:
[1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain > 5:chain:LLMChain > 6:llm:ChatOpenAI > 7:llm:ChatOpenAI]

```javascript showLineNumbers highlightLine=1-5,8
Type Your question  ('q' to exit): what is 2*3
Response: >>> 
[chain/start] [1:chain:AgentExecutor] Entering Chain run with input:
{
  "input": "what is 2*3",
  "memory": []
}
[llm/start] [1:chain:AgentExecutor > 2:llm:ChatOpenAI] Entering LLM run with input:
{
  "prompts": [
    "System: You are a helpful AI assistant.\nHuman: what is 2*3"
  ]
}
[llm/end] [1:chain:AgentExecutor > 2:llm:ChatOpenAI] [1.12s] Exiting LLM run with output:
{
  "generations": [
    [
      {
        "text": "",
        "generation_info": {
          "finish_reason": "function_call"
        },
        "message": {
          "lc": 1,
          "type": "constructor",
          "id": [
            "langchain",
            "schema",
            "messages",
            "AIMessage"
          ],
          "kwargs": {
            "content": "",
            "additional_kwargs": {
              "function_call": {
                "name": "Calculator",
                "arguments": "{\n  \"__arg1\": \"2*3\"\n}"
              }
            }
          }
        }
      }
    ]
  ],
  "llm_output": {
    "token_usage": {
      "prompt_tokens": 197,
      "completion_tokens": 19,
      "total_tokens": 216
    },
    "model_name": "gpt-3.5-turbo-16k-0613"
  },
  "run": null
}
[tool/start] [1:chain:AgentExecutor > 3:tool:Calculator] Entering Tool run with input:
"2*3"
[chain/start] [1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain] Entering Chain run with input:
{
  "question": "2*3"
}
[chain/start] [1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain > 5:chain:LLMChain] Entering Chain run with input:
{
  "question": "2*3",
  "stop": [
    "```output"
  ]
}
[llm/start] [1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain > 5:chain:LLMChain > 6:llm:ChatOpenAI] Entering LLM run with input:
{
  "prompts": [
    "Human: Translate a math problem into a expression that can be executed using Python's numexpr library. Use the output of running this code to answer the question.\n\nQuestion: ${Question with math problem.}\n```text\n${single line mathematical expression that solves the problem}\n```\n...numexpr.evaluate(text)...\n```output\n${Output of running the code}\n```\nAnswer: ${Answer}\n\nBegin.\n\nQuestion: What is 37593 * 67?\n```text\n37593 * 67\n```\n...numexpr.evaluate(\"37593 * 67\")...\n```output\n2518731\n```\nAnswer: 2518731\n\nQuestion: 37593^(1/5)\n```text\n37593**(1/5)\n```\n...numexpr.evaluate(\"37593**(1/5)\")...\n```output\n8.222831614237718\n```\nAnswer: 8.222831614237718\n\nQuestion: 2*3"
  ]
}
[llm/end] [1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain > 5:chain:LLMChain > 6:llm:ChatOpenAI] [1.34s] Exiting LLM run with output:
{
  "generations": [
    [
      {
        "text": "```text\n2 * 3\n```\n...numexpr.evaluate(\"2 * 3\")...\n",
        "generation_info": {
          "finish_reason": "stop"
        },
        "message": {
          "lc": 1,
          "type": "constructor",
          "id": [
            "langchain",
            "schema",
            "messages",
            "AIMessage"
          ],
          "kwargs": {
            "content": "```text\n2 * 3\n```\n...numexpr.evaluate(\"2 * 3\")...\n",
            "additional_kwargs": {}
          }
        }
      }
    ]
  ],
  "llm_output": {
    "token_usage": {
      "prompt_tokens": 203,
      "completion_tokens": 21,
      "total_tokens": 224
    },
    "model_name": "gpt-3.5-turbo-16k-0613"
  },
  "run": null
}
[chain/end] [1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain > 5:chain:LLMChain] [1.34s] Exiting Chain run with output:
{
  "text": "```text\n2 * 3\n```\n...numexpr.evaluate(\"2 * 3\")...\n"
}
[chain/end] [1:chain:AgentExecutor > 3:tool:Calculator > 4:chain:LLMMathChain] [1.34s] Exiting Chain run with output:
{
  "answer": "Answer: 6"
}
[tool/end] [1:chain:AgentExecutor > 3:tool:Calculator] [1.34s] Exiting Tool run with output:
"Answer: 6"
[llm/start] [1:chain:AgentExecutor > 7:llm:ChatOpenAI] Entering LLM run with input:
{
  "prompts": [
    "System: You are a helpful AI assistant.\nHuman: what is 2*3\nAI: {'name': 'Calculator', 'arguments': '{\\n  \"__arg1\": \"2*3\"\\n}'}\nFunction: Answer: 6"
  ]
}
[llm/end] [1:chain:AgentExecutor > 7:llm:ChatOpenAI] [432.821ms] Exiting LLM run with output:
{
  "generations": [
    [
      {
        "text": "The product of 2 and 3 is 6.",
        "generation_info": {
          "finish_reason": "stop"
        },
        "message": {
          "lc": 1,
          "type": "constructor",
          "id": [
            "langchain",
            "schema",
            "messages",
            "AIMessage"
          ],
          "kwargs": {
            "content": "The product of 2 and 3 is 6.",
            "additional_kwargs": {}
          }
        }
      }
    ]
  ],
  "llm_output": {
    "token_usage": {
      "prompt_tokens": 227,
      "completion_tokens": 13,
      "total_tokens": 240
    },
    "model_name": "gpt-3.5-turbo-16k-0613"
  },
  "run": null
}
[chain/end] [1:chain:AgentExecutor] [2.89s] Exiting Chain run with output:
{
  "output": "The product of 2 and 3 is 6."
}
The product of 2 and 3 is 6.
```