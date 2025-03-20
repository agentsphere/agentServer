
import re
import time
from typing import Any
from pymilvus import MilvusClient
import ollama
import logging
from markdownify import markdownify as md
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from llm import getQueriesForDocument

driver = webdriver.Chrome()

DOCLIMIT=6000
# Wait until document.readyState is 'complete'
WebDriverWait(driver, 30).until(
    lambda driver: driver.execute_script('return document.readyState') == 'complete'
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger=logging.getLogger(__name__)

def emb_text(text):
    response = ollama.embeddings(model="mxbai-embed-large", prompt=text)
    return response["embedding"]

client = MilvusClient("milvus_demo.db")

if client.has_collection(collection_name="knowledge"):
    logger.info("Dropping existing collection: knowledge")
    client.drop_collection(collection_name="knowledge")

logger.info("Creating new collection: knowledge")
client.create_collection(
    collection_name="knowldge",
    auto_id=True,
    dimension=1024,
)




import requests
from bs4 import BeautifulSoup
#from sentence_transformers import SentenceTransformer
#from vectordb import Memory


def search_vector_db(query, threshold=0.8):
    query_embedding = emb_text(query)
    res = client.search(
            collection_name="tool_collection",
            data=[query_embedding],
            limit=2,
        )
    filtered_results = [
        hit for hit in res[0] if hit.get("distance") >= threshold
    ]
    logger.info(filtered_results)
    return filtered_results


def perform_web_search(query):
    # Replace with your web search API call
    search_url = f"https://api.bing.microsoft.com/v7.0/search?q={query}"
    headers = {"Ocp-Apim-Subscription-Key": "Your_Bing_Search_API_Key"}
    response = requests.get(search_url, headers=headers)
    response.raise_for_status()
    search_results = response.json()
    return [entry['url'] for entry in search_results.get('webPages', {}).get('value', [])]

def getPageWithSelenium(url):
    driver.get(url)

    try:
        WebDriverWait(driver, 3).until(
            lambda d: d.execute_script(
                """
                return window.performance.getEntriesByType('resource')
                .filter(e => ['xmlhttprequest', 'fetch', 'script', 'css', 'iframe', 'beacon', 'other'].includes(e.initiatorType)).length === 0;
                """
            )
        )
    except Exception as e:
        print("Timeout waiting for network requests:", e)
 
    page_source = driver.page_source
    driver.quit()
    return page_source


def concatenate_strings(lst, max_char):
    result = []
    current_string = ""
    
    for s in lst:
        if len(current_string) + len(s) <= max_char:
            current_string += s  # Concatenate the string
        else:
            result.append(current_string)  # Save the previous concatenated string
            current_string = s  # Start a new string
            
    if current_string:  # Append any remaining string
        result.append(current_string)
    
    return result

def split(doc):
    
    le=len(doc.get_text(strip=True))
    if le > DOCLIMIT:
        splits=[]
        logger.info(f"break {le}")
        splitsTags= ["h1", "h2", "h3", "h4"]

        for tag in splitsTags:
            count = len(doc.find_all(tag))
            if count > 1:
                logger.info(f"finding {tag} {count}")
                
                # Regular expression pattern
                pattern = re.compile(
                    r'(?s)(.*?)'             # Text before the first <h2>
                    rf'(?:(<{tag}.*?</{tag}>))'     # Each <h2> tag
                    rf'(.*?)(?=(?:<{tag})|\Z)'   # Content after <h2> up to the next <h2> or end
                )

                # Find all matches
                matches = pattern.findall(str(doc))


                # Process and display the sections
                for i, (pre_tag, tagC, content) in enumerate(matches, start=1):
                    
                    if pre_tag.strip():
                        print(f"Section {i} (Before first <h2>):\n{pre_tag.strip()[0:100]}\n{'-'*40}")
                        s = BeautifulSoup(pre_tag.strip(), 'html.parser')
                        text = s.get_text(strip=True, separator="\n")
                        if len(text)>DOCLIMIT:
                            splits.append(split(s))
                        else:
                            do = md(str(s))
                            splits.append(do)
                        i += 1
                    if tagC:

                        print(f"Section {i} (Heading and Content):\n{tagC.strip()[0:100]}\n{content.strip()[0:100]}\n{'-'*40}")
                        s = BeautifulSoup(tagC + content, 'html.parser')
                        if len(s.get_text(strip=True))>DOCLIMIT:
                            splits.append(split(s))
                        else:
                            do = md(str(s))
                            logger.info(do)
                            splits.append(do)
        [logger.info(len(s)) for s in splits]
        n = concatenate_strings(splits, DOCLIMIT)

        [logger.info(len(s)) for s in n]
        return n
    else:
        # dont need to be split
        return [doc]

def getDocsFromHTML(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'header', "footer", "meta", "svg"]):
        tag.decompose()  # Completely removes the tag from the soup
    text_length_per_parent = {}
    total_length = len(soup.get_text(strip=True))
    if total_length == 0:
        return

    # Iterate over all elements and count text length
    for element in soup.find_all():
        text_length = len(element.get_text(strip=True))
        ratio = text_length / total_length
        if ratio < 0.7: # i dont want 
            break
        ratio=text_length/total_length
        text_length_per_parent[ratio] = element

    _, main = min(text_length_per_parent.items(), key=lambda x: abs(x[0] - 0.8))
    le=len(main.get_text(strip=True))
    if le > DOCLIMIT:
        logger.info(f"break {le}")
        return split(main)
   

def extract_text_from_url(url):

    docs = getDocsFromHTML(getPageWithSelenium(url))
    for doc in docs:
        queries = getQueriesForDocument(doc)
        logger.info(f"{queries}")
    # Extract main content based on HTML structure
    #paragraphs = soup.find_all('p')
    #text_content = ' '.join([para.get_text() for para in paragraphs])
    #return text_content
    return "fin"



if __name__ == "__main__":
    try:
        url= "https://ai.pydantic.dev/"
        logger.info(extract_text_from_url(url))
    except KeyboardInterrupt:
        logging.info("Server shutdown requested. Exiting cleanly.")





#def store_chunks_in_vectordb(chunks):
#    for chunk in chunks:
#        embedding = embedding_model.encode(chunk, convert_to_tensor=True)
#        memory.add({'text': chunk, 'embedding': embedding})

def fetch_knowledge(query):
    # Step 1: Search vectorDB
    result = search_vector_db(query)
    if result:
        return result

    # Step 2: Perform web search
    urls = perform_web_search(query)

    # Step 3: Extract and process information from websites
    for url in urls:
        text = extract_text_from_url(url)
        chunks = chunk_text(text)
        #store_chunks_in_vectordb(chunks)

    # Step 4: Retry vectorDB search after updating it
    result = search_vector_db(query)
    return result

# Example usage
#query = "Python web scraping libraries"
#knowledge = fetch_knowledge(query)
#print(knowledge)



toolQueries = [
    {"query": "lets setup a postgres", "tool": "bash sh"},
    {"query": "lets create a PR", "tool": "bash sh"},
    {"query": "insert into postgres", "tool": "bash sh"},
    {"query": "commit in repo", "tool": "bash sh"}
]

def addQuery(query):
    """Adds a query to the Milvus vector database with proper error handling."""
    try:
        if not query or not query.get("query") or not query.get("tool"):
            logger.warning("Invalid query data provided. Skipping insertion.")
            return

        logger.info(f"Generating embedding for query: {query.get('query')}")
        vector = emb_text(query.get("query"))

        logger.info(f"Inserting query into collection: {query.get('query')} -> {query.get('tool')}")
        client.insert(
            collection_name="tool_collection",
            data=[{"vector": vector, "text": query.get("query"), "tool": query.get("tool")}]
        )
        logger.info(f"Successfully added query: {query.get('query')} with tool: {query.get('tool')}")
    except Exception as e:
        logger.error(f"Error inserting query into Milvus: {e}")

#[addQuery(t) for t in toolQueries]