from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def create_qa_chain(llm, vectorstore):
    condense_question_system_template = """Given a conversation history and the latest user question which may reference context from previous interactions, formulate a standalone search query that will help retrieve the most relevant information from the organization's policy documents. 

    Your task is to:
    1. Identify the core information need in the user's question
    2. Extract any specific terms, policies, or concepts that should be included in the search
    3. Reformulate ambiguous references (like "it", "that policy", "this benefit") into explicit terms
    4. Include important contextual keywords that will improve retrieval accuracy
    5. Focus on creating a clear, concise query that will return the most relevant document chunks

    Do NOT answer the query yourself, just create an optimized search query. If the original question is already clear and specific, you may return it as-is.
        
    Organization Policy Context:
        [Insert relevant sections of the organization's policy documents here]

        Reformulated Query:"""

    condense_question_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", condense_question_system_template),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, vectorstore.as_retriever(search_kwargs={"k": 30}), condense_question_prompt
    )

    system_prompt = """You are an expert . You MUST ONLY provide information that is explicitly present in the retrieved context. Your answers must be based SOLELY on the documents provided in the context section.

        IMPORTANT RULES:
        1. If the information requested is not present in the provided context, you MUST respond with "I don't know" or "I don't have that information in my knowledge base."
        2. Never make up information or infer details that aren't explicitly stated in the context.
        3. Provide concise answers within 70 words unless the user specifically asks for more detail.
        4. Do not use markdown formatting in your responses.
        5. Answer in the same language as the question.
        6. Do not reference your limitations or that you are an AI.
        7. When the answer is in the context, provide it clearly and directly.
        8. Only answer questions related to HR policies, benefits, and procedures.
        9. For queries outside of HR topics, politely state you can only help with HR-related matters.
        10. Do not attempt to calculate dates or make determinations not explicitly stated in the context.

        Current Date: {current_date}

        Context: {context}

        """

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{current_date}"),
            ("human", "{input}"),
        ]
    )
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)

    convo_qa_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    return convo_qa_chain

def create_checker_chain(llm):
    # Implementation of checker chain if needed
    pass

def check_answer_type_chain(llm):
    # Implementation of answer type checker if needed
    pass