import os
import pickle
import base64
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pypdf import PdfReader  # لقراءة ملفات الـ PDF

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def extract_text_from_pdf(pdf_path):
    """دالة لقراءة النصوص من ملف الـ PDF"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def fetch_and_process_cvs(service):
    print("Searching for CV emails and attachments...")
    # إنشاء مجلد لحفظ المرفقات إذا لم يكن موجوداً
    if not os.path.exists('downloaded_cvs'):
        os.makedirs('downloaded_cvs')

    # البحث عن الإيميلات المتعلقة بالسير الذاتية
    query = "cv OR resume OR سيره ذاتيه"
    results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No CV emails found matching the criteria.")
        return

    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = txt['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        
        print(f"\n[Found Email]")
        print(f"  From: {sender}")
        print(f"  Subject: {subject}")
        
        # فحص أجزاء الرسالة للبحث عن المرفقات
        parts = txt['payload'].get('parts', [])
        for part in parts:
            filename = part.get('filename')
            if filename:
                print(f"  -> Attachment found: {filename}")
                attachment_id = part['body'].get('attachmentId')
                
                if attachment_id:
                    # تحميل المرفق من Gmail API
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=msg['id'], id=attachment_id
                    ).execute()
                    
                    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                    file_path = os.path.join('downloaded_cvs', filename)
                    
                    # حفظ الملف في مجلد downloaded_cvs
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    print(f"  -> Saved successfully to: {file_path}")
                    
                    # إذا كان الملف PDF، نقوم بقراءة محتواه واستخراج النص
                    if filename.lower().endswith('.pdf'):
                        cv_text = extract_text_from_pdf(file_path)
                        print(f"  -> Extracted CV Text Preview (first 200 chars):")
                        print(f"     {cv_text[:200]}...")

if __name__ == '__main__':
    print("Connecting to Gmail API...")
    service = authenticate_gmail()
    print("Successfully connected to Gmail!")
    
    fetch_and_process_cvs(service)