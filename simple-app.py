import streamlit as st
import uuid
import warnings
import io
import os
import boto3
import openai
from langchain_voyageai import VoyageAIEmbeddings
from urllib.parse import urlparse
from pinecone import Pinecone
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain, RetrievalQA
from langchain_pinecone import PineconeVectorStore
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage
from langchain.prompts import ChatPromptTemplate
from langchain.chains import ConversationChain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


# Ignore all warnings
warnings.filterwarnings("ignore")

# Set up Streamlit app
st.set_page_config(page_title="Jarvis", layout="wide")
st.title("Jarvis Healthcare V1.0")

# Setu up secrets & necessary objeccts
OPENAI_API_KEY = st.secrets["api_keys"]["OPENAI_API_KEY"]
VOYAGE_AI_API_KEY = st.secrets["api_keys"]["VOYAGE_AI_API_KEY"]
PINECONE_API_KEY = st.secrets["api_keys"]["PINECONE_API_KEY"]
aws_access_key_id = st.secrets["aws"]["aws_access_key_id"]
aws_secret_access_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]

s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

# Function to generate pre-signed URL
def generate_presigned_url(s3_uri):
    parsed_url = urlparse(s3_uri)
    bucket_name = parsed_url.netloc
    object_key = parsed_url.path.lstrip('/')
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_key},
        ExpiresIn=3600
    )
    return presigned_url

# Function to retrieve documents, generate URLs, and format the response
def retrieve_and_format_response(query, retriever, llm, chat_history):
    docs = retriever.get_relevant_documents(query)
    
    formatted_docs = []
    for doc in docs:
        content_data = doc.page_content
        s3_uri = doc.metadata['id']
        s3_gen_url = generate_presigned_url(s3_uri)
        formatted_doc = f"{content_data}\n\n[More Info]({s3_gen_url})"
        formatted_docs.append(formatted_doc)
    
    combined_content = "\n\n".join(formatted_docs)
    
    # Create a prompt for the LLM to generate an explanation based on the retrieved content
    prompt = f"Instruction: You are a helpful assistant to help users with their patient education queries. \
               Based on the following information, provide a summarized & concise explanation using a couple of sentences. \
               Only respond with the information relevant to the user query {query}, \
               if there are none, make sure you say the `magic words`: 'I don't know, I did not find the relevant data in the knowledge base.' \
               But you could carry out some conversations with the user to make them feel welcomed and comfortable, in that case you don't have to say the `magic words`. \
               In the event that there's relevant info, make sure to attach the download button at the very end: \n\n[More Info Download]({s3_gen_url}) \
               Context: {combined_content} \
               Chat History: {chat_history}"
    
    # Originally there were no message
    message = HumanMessage(content=prompt)

    response = llm([message])
    return response



# Function to save chat history to a string
def save_chat_history(messages):
    chat_history= "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
    return chat_history

# Function to upload the file(object) to S3
def upload_to_s3(file, bucket_name, secret_data, key):
    s3 = boto3.client(
        's3',
        aws_access_key_id=secret_data["aws_access_key_id"],
        aws_secret_access_key=secret_data["aws_secret_access_key"],
        region_name=secret_data["aws_region"]  # Replace with your AWS region
    )

    try:
        s3.put_object(Body=file, Bucket=bucket_name, Key=key)
        print(f"File '{file.name}' uploaded to '{bucket_name}'")
    except Exception as e:
        print(f'Upload failed: {e}\n')



# Langchain stuff
llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY)

# Initialize the conversation memory
memory = ConversationBufferMemory()

prompt_template = ChatPromptTemplate.from_template(
        "Instruction: You are a helpful assistant to help users with their patient education queries. \
        Based on the following information, provide a summarized & concise explanation using a couple of sentences. \
        Only respond with the information relevant to the user query {query}, \
        if there are none, make sure you say the `magic words`: 'I don't know, I did not find the relevant data in the knowledge base.' \
        But you could carry out some conversations with the user to make them feel welcomed and comfortable, in that case you don't have to say the `magic words`. \
        In the event that there's relevant info, make sure to attach the download button at the very end: \n\n[More Info]({s3_gen_url}) \
        Context: {combined_content}"
    )

# Initialize necessary objects
# PINECONE
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "healthcare-ai"
openai.api_key = OPENAI_API_KEY

# Set up LangChain objects
# VOYAGE AI
model_name = "voyage-large-2"  
embedding_function = VoyageAIEmbeddings(
    model=model_name,  
    voyage_api_key=VOYAGE_AI_API_KEY
)
# Initialize the Pinecone client
vector_store = PineconeVectorStore.from_existing_index(
    embedding=embedding_function,
    index_name=index_name
)
retriever = vector_store.as_retriever()

# Initialize rag_chain
rag_chain = (
    {"retrieved_context": retriever, "question": RunnablePassthrough()}
    | prompt_template
    | llm
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []


# Create session and key for saving/pushing chat history
session_id = str(uuid.uuid4())
chat_history_key = f"raw-data/chat_history_{session_id}.txt"
bucket_name = "demo-chat-history-xin"

chat_history_text = save_chat_history(st.session_state["messages"])
file_obj = io.BytesIO(chat_history_text.encode('utf-8'))


st.sidebar.title("Welcome!")
st.sidebar.caption("Welcome to Javris, your personal healthcare chatbot! We're here to assist you with all your healthcare needs, \
                   providing accurate and timely information to ensure your well-being.")
st.sidebar.caption("To help us improve our services and better support you and others, you can choose to upload your chat history. \
                   Rest assured, all sensitive information will be desensitized before being stored in our database, ensuring your privacy and security.")
st.sidebar.caption("Thank you for helping us make Javris better for everyone!")

if st.sidebar.button("Help us"):
    chat_history_text = save_chat_history(st.session_state["messages"])
    file_obj = io.BytesIO(chat_history_text.encode('utf-8'))
    upload_to_s3(file_obj, bucket_name, st.secrets["aws"],chat_history_key)

st.sidebar.download_button(label = "Download the session", data = file_obj, file_name = f"chat_history_{session_id}.txt", mime = "text/plain")
# Display chat messages from history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Get user input
user_input = st.chat_input("You: ")

if user_input:
    # Add user message to chat history
    st.session_state["messages"].append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Generate and display bot response
    with st.spinner("Thinking..."):
        chat_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state["messages"]])
        bot_response = retrieve_and_format_response(user_input, retriever, llm, chat_history).content
    
    st.session_state["messages"].append({"role": "assistant", "content": bot_response})
    
    with st.chat_message("assistant"):
        st.markdown(bot_response)
