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

import streamlit as st

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



# Streamlit arayüzü
if __name__ == "__main__":
    st.set_page_config(page_title="SQL Sohbet Asistanı", page_icon="💬")
    
    # Session state yönetimi
    if "session_id" not in st.session_state:
        st.session_state.session_id = "streamlit-session-1"
        session_data = get_session_history(st.session_state.session_id)
        st.session_state.chat_history = session_data['chat_history']
        st.session_state.sql_history = session_data['sql_history']
    
    # Sidebar
    with st.sidebar:
        st.title("Ayarlar")
        st.session_state.temperature = st.slider("Model Yaratıcılık Seviyesi", 0.0, 1.0, 0.3)
        st.session_state.show_sql = st.checkbox("SQL Sorgularını Göster", value=True)
        if st.button("Sohbet Geçmişini Temizle"):
            st.session_state.chat_history.clear()
            st.session_state.sql_history.clear()
            st.rerun()
    
    # Ana sayfa
    st.title("💬 SQL Sohbet Asistanı")
    st.caption("Veritabanınızla konuşan akıllı asistan")
    
    # Sohbet geçmişini göster
    for msg in st.session_state.chat_history.messages:
        with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
            st.write(msg.content)
    
    # Kullanıcı girişi
    if prompt := st.chat_input("Sorunuzu yazın"):
        with st.chat_message("user"):
            st.write(prompt)
        
        try:
            with st.chat_message("assistant"):
                with st.spinner("Düşünüyorum..."):
                    if is_sql_question(prompt, db.get_table_info()):
                        # SQL sorgusu üret
                        sql_query = sql_chain.invoke({
                            "schema": db.get_table_info(),
                            "question": prompt
                        })
                        sql_query = clean_sql_output(sql_query)
                        sql_query = normalize_sql(sql_query)
                        
                        if st.session_state.show_sql:
                            with st.expander("Oluşturulan SQL Sorgusu"):
                                st.code(sql_query, language="sql")
                        
                        # Sorguyu çalıştır
                        with engine.connect() as conn:
                            result = conn.execute(text(sql_query))
                            rows = result.fetchall()
                        
                        if rows:
                            result_str = "\n".join(str(row) for row in rows[:5])
                            if len(rows) > 5:
                                result_str += f"\n...({len(rows)-5} sonuç daha)"
                            
                            # Sonuçları açıkla
                            explanation = explanation_chain.invoke({
                                "question": prompt,
                                "sql_query": sql_query,
                                "query_results": result_str
                            })
                            st.write(explanation)
                            
                            # Geçmişe ekle
                            st.session_state.chat_history.add_message(HumanMessage(content=prompt))
                            st.session_state.chat_history.add_message(AIMessage(content=explanation))
                        else:
                            st.warning("Sorgu sonucu bulunamadı")
                            st.session_state.chat_history.add_message(HumanMessage(content=prompt))
                            st.session_state.chat_history.add_message(AIMessage(content="Sorgu sonucu bulunamadı"))
                    else:
                        # Genel sohbet
                        response = general_chain.invoke(
                            {"question": prompt, "history": st.session_state.chat_history.messages},
                            config={"configurable": {"session_id": st.session_state.session_id}}
                        )
                        st.write(response)
                        
                        st.session_state.chat_history.add_message(HumanMessage(content=prompt))
                        st.session_state.chat_history.add_message(AIMessage(content=response))
        
        except Exception as e:
            st.error(f"Bir hata oluştu: {str(e)}")
            st.session_state.chat_history.add_message(HumanMessage(content=prompt))
            st.session_state.chat_history.add_message(AIMessage(content=f"Hata: {str(e)}"))