import os
import sys
import urllib.parse
from dotenv import load_dotenv
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
import psycopg2
from typing import List, Optional, Dict, Any, Tuple

load_dotenv()
print("Attempting to load configuration from environment variables...")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "Budget_Gov")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not found.")
    sys.exit(1)

print("Configuration loaded:")
print(f"  DB User: {DB_USER}")
print(f"  DB Password: {'Set (Hidden)' if DB_PASSWORD else 'Not Set'}")
print(f"  DB Host: {DB_HOST}")
print(f"  DB Port: {DB_PORT}")
print(f"  DB Name: {DB_NAME}")

encoded_password = urllib.parse.quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"Database URI: postgresql+psycopg2://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")

db = None
llm = None

try:
    print("Initializing database connection for schema inspection...")
    db = SQLDatabase.from_uri(DATABASE_URI)
    print("Schema inspection connection successful.")
except Exception as e:
    print(f"Error connecting to database for schema inspection: {e}")
    sys.exit(1)

try:
    print("Initializing OpenAI LLM...")
    llm = OpenAI(api_key=OPENAI_API_KEY, temperature=0)
    print("OpenAI LLM initialized successfully.")
except Exception as e:
    print(f"Error initializing OpenAI LLM: {e}")
    sys.exit(1)

SQL_PROMPT_TEMPLATE = """You are a PostgreSQL expert. Given an input question, create a syntactically correct PostgreSQL query to run.
Query for at most {top_k} results using LIMIT. Order results if helpful.
Query only the necessary columns. Wrap column names in double quotes (").
Use only columns listed in the table info. Check which table has which column.
If the question seems unrelated to budget, posts, or expenses, return "UNRELATED_QUERY_ATTEMPT".
Return only the SQL query or "UNRELATED_QUERY_ATTEMPT". No explanations.

Use this table information:
{table_info}

-- Examples --

Question: What is the basic pay for the Collector in Mumbai City?
SQL Query: SELECT "BasicPay" FROM budget_post_details WHERE "District" = 'Mumbai City' AND "Designation" = 'Collector';

Question: Show actual expenditure for Salary in Palghar for 2022-2023.
SQL Query: SELECT "ActualAmountExpenditure20222023" FROM unit_expenditure WHERE "District" = 'Palghar' AND "PrimaryAndSecondaryUnitsOfAccount" = '01- Salary';

Question: Total filled posts for temporary Class 4 in Thane?
SQL Query: SELECT SUM("FilledPosts") FROM post_expenses WHERE "District" = 'Thane' AND "Category" = 'Temporary' AND "Class" = '4';

-- End Examples --

Question: {input}
SQL Query:"""

SQL_PROMPT = PromptTemplate(
    input_variables=["input", "top_k", "table_info"],
    template=SQL_PROMPT_TEMPLATE
)

RESPONSE_PROMPT_TEMPLATE = """
You are a helpful assistant answering questions about budget and staffing data (budget post details, post status, post expenses, unit expenditure) based on information retrieved from the system.
The user asked the following question:
"{question}"

The system retrieved the following relevant information (or status message):
{results}

Follow these steps carefully to formulate your answer to the user, using simple and non-technical language:
1. Check if the 'results' indicate an error (e.g., contains "DATABASE_ERROR", "GENERAL_ERROR"). If yes, state politely that a technical problem occurred while accessing the required information.
2. Check if the 'results' indicate "NO_RECORDS_FOUND". If yes, state clearly that no information matching the specific criteria was found. Suggest checking spelling or trying slightly different terms if appropriate.
3. Check if the 'results' indicate "UNRELATED_QUERY_ATTEMPT" or "Could not generate query.". If yes, politely inform the user that you can only answer questions about the available budget, staffing, and expenditure details, and ask them to rephrase their question to focus on those topics.
4. Check if the 'results' contain actual data, but the original 'question' was very broad. If so, briefly describe the *kind* of information found (e.g., "I found details about pay and allowances for various posts...") and politely ask the user to be more specific about what they need (e.g., "Could you specify which post or allowance you're interested in for a more detailed answer?").
5. If the 'results' contain data that directly answers the specific 'question', provide a concise answer in simple language, based *only* on the provided 'results'. Do not use jargon like 'query', 'columns', 'database'.
6. If none of the above seem to fit, state that you couldn't find a clear answer with the available information and suggest they rephrase the question.

Answer:
"""

RESPONSE_PROMPT = PromptTemplate(
    input_variables=["question", "results"],
    template=RESPONSE_PROMPT_TEMPLATE
)

sql_chain = None
if llm and db:
    print("Creating SQL query chain...")
    sql_chain = create_sql_query_chain(llm=llm, db=db, prompt=SQL_PROMPT)
    print("SQL query chain created.")
else:
    print("Error: LLM or DB object not initialized. SQL chain not created.")

def execute_query(query: str):
    if not query or query.isspace():
        return "Could not generate query."
    if query.strip().upper() == "UNRELATED_QUERY_ATTEMPT":
        return "UNRELATED_QUERY_ATTEMPT"

    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        cursor = conn.cursor()
        print(f"Executing SQL: {query}")
        cursor.execute(query)
        if cursor.description:
            results = cursor.fetchall()
            print(f"Query returned {len(results)} rows.")
        else:
            results = f"Operation successful, {cursor.rowcount} rows affected."
            print(results)
        cursor.close()
        return results
    except psycopg2.Error as e:
        error_message = f"DATABASE_ERROR: Code {e.pgcode} - {e.pgerror}"
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"GENERAL_ERROR: {str(e)}"
        print(error_message)
        return error_message
    finally:
        if conn:
            conn.close()

def generate_response(question: str, results: Any):
    if not llm:
         return "Error: LLM not initialized."

    if isinstance(results, str):
        results_str = results
    elif not results:
         results_str = "NO_RECORDS_FOUND"
    else:
        max_results_for_prompt = 10
        results_str = str(results[:max_results_for_prompt])
        if len(results) > max_results_for_prompt:
            results_str += f"\n... (truncated, {len(results) - max_results_for_prompt} more rows)"

    if not results_str:
        results_str = "No information was retrieved."

    try:
        response_chain = RESPONSE_PROMPT | llm
        final_response = response_chain.invoke({
            "question": question,
            "results": results_str
        })
        return final_response.strip()
    except Exception as e:
        print(f"Error generating final response with LLM: {e}")
        return "Sorry, I encountered an error while formulating the final response."

def chatbot(question: str):
    print("\n--- Processing new question ---")
    if not sql_chain:
        return "Error: SQL Chain not initialized properly."

    generated_query = "Error in processing"
    results = "Error: Could not determine query."
    try:
        print(f"Generating SQL for question: {question}")
        query_result = sql_chain.invoke({"question": question})
        generated_query = query_result.strip()
        print(f"Generated SQL/Response: {generated_query}")

        llm_refusal_starts = ("i don't know", "i cannot", "sorry")
        if not generated_query or generated_query == "UNRELATED_QUERY_ATTEMPT" or generated_query.lower().startswith(llm_refusal_starts):
            print(f"LLM indicated invalid/unrelated query or failed: '{generated_query}'")
            results = generated_query if generated_query else "Could not generate query."
        else:
            print("Executing generated SQL query or handling status...")
            results = execute_query(generated_query)

    except Exception as e:
        print(f"Error during SQL query generation or execution phase: {e}")
        results = f"GENERAL_ERROR: {str(e)}"

    print("Generating final response...")
    response = generate_response(question, results)
    print("--- Finished processing question ---")
    return response