import streamlit as st
import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor
import callbacks

load_dotenv()

from chain_setup import setup_agent

QUESTION_HISTORY: str = 'question_history'


def init_stream_lit():
    title = "LEGO Assembly Training Assistant"
    st.set_page_config(page_title=title, page_icon="🦜", layout="wide")
    st.header(title)

    # Setup credentials in Streamlit
    user_openai_api_key = st.sidebar.text_input(
        "OpenAI API Key", type="password", help="Set this to run your own custom questions."
    )

    if user_openai_api_key or os.environ['OPENAI_API_KEY']:
        enable_custom = True
    else:
        enable_custom = False

    if QUESTION_HISTORY not in st.session_state:
        st.session_state[QUESTION_HISTORY] = []
    intro_text()
    simple_chat_tab, historical_tab = st.tabs(["Simple Chat", "Session History"])
    with simple_chat_tab:
        if enable_custom:
            os.environ['OPENAI_API_KEY'] = user_openai_api_key if not os.environ['OPENAI_API_KEY'] else os.environ['OPENAI_API_KEY']
            agent_executor: AgentExecutor = prepare_agent()
            user_question = st.text_input("Your question")
        else:
            st.error(f"Please enter your API Keys in the sidebar to ask your own custom questions.")
        with st.spinner('Please wait ...'):
            try:
                response = agent_executor.run(user_question, callbacks=[callbacks.StreamlitCallbackHandler(st)])    # ! Important to have a streaming callback handler.
                st.write(f"TA Answer:\n{response}")
                st.session_state[QUESTION_HISTORY].append((user_question, response))
            except Exception as e:
                st.error(f"Error occurred: {e}")
    with historical_tab:
        for q in st.session_state[QUESTION_HISTORY]:
            question = q[0]
            if len(question) > 0:
                st.write(f"Q: {question}")
                st.write(f"A: {q[1]}")


def intro_text():
    with st.expander("Click to see application info:"):
        st.write(f"""Hi, I am your digital trainer to teach you how to assemble a LEGO car. \n
        Feel free to ask me open questions or questions about LEGO Assemble Task. \n
        We are providng the following functional services in our XR application.\n
        1	StartAssemble	to initiate the assembly process.\n
        2	NextStep	to move to the next assembly step.\n
        3	FrontStep	to go back to the previous assembly step.\n
        4	Explode	to trigger an explosion for detailed viewing.\n
        5	Recover	to restore the initial state of the VR objects after explosion.\n
        6	FinishedVideo	to end the assembly process and show a video of the assembled LEGO bricks.\n
        7	ReShow	to repeat the current assembly step.\n
        8	Enlarge	to enlarge or zoom out the current object.\n
        9	Shrink	to shrink or zoom in the current object.\n
    """)

@st.cache_resource()
def prepare_agent() -> AgentExecutor:
    return setup_agent()


if __name__ == "__main__":
    init_stream_lit()