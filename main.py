from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from sqlalchemy import create_engine, text

from dotenv import load_dotenv

import os

import re


load_dotenv()

# Model konfigurasyonu
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.3
)

# Veri tabani baglantisinin saglanmasi
db_uri = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
db = SQLDatabase.from_uri(db_uri)
engine = create_engine(db_uri)


# SQL uretilmesi icin prompt
sql_prompt = PromptTemplate.from_template("""
Veritabanı şemasını kullanarak aşağıdaki soruya uygun BİR SQL sorgusu oluştur:

VERİTABANI ŞEMASI:
{schema}

KULLANICI SORUSU:
{question}

SADECE SQL KODU (açıklama yok, ``` yok):
""")

# LLM cevapları icin prompt
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "Kullanıcının sorularına dostça ve yardımcı olacak şekilde Türkçe yanıt ver."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

# SQL sonucunu kullaniciya aciklayan prompt
explanation_prompt = ChatPromptTemplate.from_messages([
    ("system", "SQL sorgusu sonuçlarını kullanıcıya anlaşılır şekilde açıkla:"),
    ("human", """
    SORU: {question}
    
    SQL: {sql_query}
    
    SONUÇLAR: {query_results}
    
    AÇIKLAMA:
    """)
])

# Chains
sql_chain = sql_prompt | model | StrOutputParser()
general_chain = chat_prompt | model | StrOutputParser()
explanation_chain = explanation_prompt | model | StrOutputParser()

# SQL normalizasyon fonksiyonu
def normalize_sql(sql_query):
    sql_query = re.sub(r'(\b(FROM|JOIN|WHERE|GROUP BY|ORDER BY|HAVING)\b)(?![ ])', r'\1 ', sql_query, flags=re.IGNORECASE)
    return sql_query.strip()

# Soru tipini belirleme fonksiyonu
def is_sql_question(question, schema):
    # SQL anahtar kelimeleri
    sql_keywords = ["select", "insert", "update", "delete", "from", "where", 
                   "join", "group by", "order by", "having", "limit", "offset",
                   "count", "sum", "avg", "max", "min", "distinct"]
    
    # Veritabani bilgilerini al
    table_names = [table.lower() for table in db.get_usable_table_names()]
    column_names = []
    
    # Tum tablolardaki sutun isimlerini al
    for table in db.get_usable_table_names():
        table_info = db.get_table_info(table_names=[table])

        columns = re.findall(r'"(\w+)"\s+\w+', table_info)
        column_names.extend([col.lower() for col in columns])
    
    question_lower = question.lower()
    
    # SQL anahtar kelimesi kontrol
    if any(keyword in question_lower for keyword in sql_keywords):
        return True
    
    # Tablo adi kontrol
    if any(table in question_lower for table in table_names):
        return True
        
    # Sutun adi kontrol
    if any(len(col) > 3 and col in question_lower for col in column_names):
        return True
    
    # Veriye dair spesifik ifadeler
    data_related_phrases = [
        "listele", "göster", "bul", "getir", "sayısı", 
        "miktarı", "tarihi", "filtrele", "sorgula", "rapor"
    ]
    if any(phrase in question_lower for phrase in data_related_phrases):
        return True
        
    return False

# Chat history tutulmasi
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = {
            'chat_history': InMemoryChatMessageHistory(),
            'sql_history': InMemoryChatMessageHistory()
        }
    return store[session_id]

# SQL'den markdown ve kod bloklarını temizleme
def clean_sql_output(sql_query):
    # ```sql ve ``` temizle
    sql_query = re.sub(r'```sql|```', '', sql_query)
    # Baştaki ve sondaki boşlukları temizle
    return sql_query.strip()

if __name__ == "__main__":
    
    session_id = "user-session-1"
    session_data = get_session_history(session_id)
    chat_history = session_data['chat_history']
    sql_history = session_data['sql_history']
    
    while True:
        question = input("\nSoru (Çıkış için 'q'): ").strip()
        if question.lower() == 'q':
            break

        try:
            if is_sql_question(question, db.get_table_info()):
                # SQL için geçmişi temizle (sadece son 1-2 mesajı tut)
                clean_messages = chat_history.messages[-2:] if len(chat_history.messages) > 2 else chat_history.messages
                
                sql_query = sql_chain.invoke({
                    "schema": db.get_table_info(),
                    "question": question,
                    "history": clean_messages  
                })
                
                # SQL'i sorgusunun temizlenmesi
                sql_query = clean_sql_output(sql_query)
                sql_query = normalize_sql(sql_query)
                print(f"\n[SQL Sorgusu]:\n{sql_query}")

                # SQL history'e kaydet
                sql_history.add_message(HumanMessage(content=question))
                sql_history.add_message(AIMessage(content=sql_query))

                with engine.connect() as conn:
                    result = conn.execute(text(sql_query))
                    rows = result.fetchall()

                if rows:
                    result_str = "\n".join(str(row) for row in rows[:5])
                    if len(rows) > 5:
                        result_str += f"\n...({len(rows)-5} sonuç daha)"
                    
                    explanation = explanation_chain.invoke({
                        "question": question,
                        "sql_query": sql_query,
                        "query_results": result_str
                    })
                    print(f"\n[SONUÇ]:\n{explanation}")
                    
                    # Chat history'e sonuc kisimlarinin eklenmesi
                    chat_history.add_message(HumanMessage(content=question))
                    chat_history.add_message(AIMessage(content=explanation))
                else:
                    print("\nSonuç bulunamadı")
                    chat_history.add_message(HumanMessage(content=question))
                    chat_history.add_message(AIMessage(content="Sorgu sonucu bulunamadı"))
            
            else:
                # SQL ile ilgili olmayan kisimlarda LLM ile cevaplandirmalar
                print("\n[Yanıt]: ", end="")
                response = general_chain.invoke(
                    {"question": question, "history": chat_history.messages},
                    config={"configurable": {"session_id": session_id}}
                )
                print(response)
                
                chat_history.add_message(HumanMessage(content=question))
                chat_history.add_message(AIMessage(content=response))

        except Exception as e:
            error_msg = f"Üzgünüm, bir hata oluştu: {str(e)}"
            print(f"\n[ERROR]: {error_msg}")
            chat_history.add_message(HumanMessage(content=question))
            chat_history.add_message(AIMessage(content=error_msg))