# SQL Assistant Project with Langchain

Bu çalışmada Google AI tarafından geliştirilen yapay zekâ Gemini API'ı ve Langchain SQL framework'ü kullanılarak bir SQL asistanı projesi geliştirilmiştir.

Projede __.env__ dosyasında içeriğinde şu veriler bulunmaktadır.

• GEMINI_API_KEY

• LANGCHAIN_API_KEY

• LANGCHAIN_TRACING_V2=true

• LANGCHAIN_PROJECT=PROJECT_NAME

• DB_USER

• DB_PASSWORD

• DB_HOST

• DB_PORT

• DB_NAME


Projede, Gemini AI ile birlikte Langchain SQL framework'ü kullanılmıştır. Langchain, büyük dil modelleri ile uygulama geliştirilmesinde kullanılmaktadır. Zincir yapısında LLM'lerin birbirleri ile ve insanlar ile konuşmasını sağlamaktadır. Doküman okuma-yükleme, chat geçmişi tutma, embedding işlemleri ve vektör database işlemleri için langchain framework'ünden faydalanılmıştır. LangChain, LLM'ler ile entegrasyon sağlayarak özelleştirilmiş sorgu yönetimi sunmaktadır. Langchain'in sağladığı Langchain SQL hizmeti ise kullanılan veri tabanı ile bağlantı sağlanmasını ve SQL sorgularının veri tabanında çalıştırılmasını sağlamaktadır.

Bu çalışmada veri tabanı olarak PostgreSQL kullanılmıştır. __SQLDatabase__ ile veri tabanı bağlantılı sağlanmıştır. Bağlantı için gerekli bilgiler .env dosyasında yer almaktadır. Buradaki bilgiler ile veri tabanı bağlantısı sağlandıktan sonra SQL sorguları veri tabanında çalışır hale gelmiştir.

<br>
Çalışmada kurulan algoritmanın genel yapısı Şekil 1'de görülmektedir.
<br>
<div align="center">
<img src="https://github.com/user-attachments/assets/9bfd121d-24cf-4d60-9384-f985261402d7" alt="image">
</div>
Şekil 1. Kurulan algoritmanın genel şeması ve akışı


<br>
Şekil 1'de görüldüğü üzere kullanıcıdan alınan input ilk olarak bir sql sorgusu istiyor mu yoksa sadece LLM ile cevap verilebilir mi kontrol edilmektedir. Veri tabanındaki tablo ile ilgili bilgiler içeren ve SQL üzerinden bilgi verilebilecek sorular SQL chain yapısına yönlendirilmektedir. Burada SQL query hazırlaması için oluşturulan prompt ile soruya uygun bir SQL query oluşturulmaktadır. Oluşturulan query veri tabanında çalıştırılarak bir sonuç elde edilmektedir. Burada elde edilen sonuç LLM ile birleştirilerek kullanıcıya açıklayıcı bir biçimde sunulmaktadır. 

Eğer SQL ile cevaplanacak bir soru sorulmamış ise bu sefer kod direkt LLM üzerinden cevap vermektedir.

Bu yapının sağlaması için  3 adet prompt ve chain yapısı tanımlanmıştır. Bunlar sırasıyla SQL sorguları üretilmesi için,  SQL sonucunu LLM ile açıklamak için ve soruyu doğrudan LLM ile yanıtlamak içindir. Şekil 1'de bu bahsedilen adımlar detaylı olarak gösterilmektedir.

Çalışmada chat history tutularak asistan ile daha tutarlı ve kolay iletişim sağlanmıştır.

Bunlara ek olarak kullanım kolaylığı ve görsellik katmak için streamlit ile bir arayüz tasarlanmıştır. Tasarlanan arayüz çıktıları ve terminal çıktıları örnekleri aşağıda yer almaktadır.

<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/f45bf07a-427b-45f8-a1f9-2a760d482fbc" alt="image">
</div>
Şekil 2. Örnek terminal çıktısı
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/c9117be6-89b6-4832-af6e-20e99fb5cdb2" alt="image">
</div>
Şekil 3. Örnek terminal çıktısı
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/5faf42b1-2e6f-42e2-a1f8-036fe08ce63d" alt="image">
</div>
Şekil 4. Örnek terminal çıktısı
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/19758a58-802b-4988-86c6-277efb419411" alt="image">
</div>
Şekil 5. Örnek terminal çıktısı
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/9d13d30e-6419-4804-ae4b-5b56747ea2a0" alt="image">
</div>
Şekil 6. Örnek terminal çıktısı - Chat history
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/26099153-f916-4115-b964-cdc821111f9d" alt="image">
</div>
Şekil 7. Örnek streamlit ui çıktısı
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/805243fb-5cbd-46ca-9fc9-96d67e318b47" alt="image">
</div>
Şekil 8. Örnek streamlit ui çıktısı
<br>
<br>

<div align="center">
<img src="https://github.com/user-attachments/assets/8f67ae50-28db-481e-9928-a20503cef380" alt="image">
</div>
Şekil 9. Örnek streamlit ui çıktısı
<br>
<br>
