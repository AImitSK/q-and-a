from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import PyPDF2
import openai
from dotenv import load_dotenv
from flask_cors import CORS
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Laden der Umgebungsvariablen aus der .env-Datei
load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

openai.api_key = os.getenv('OPENAI_API_KEY')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
    return text

def get_embeddings(text):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response['data'][0]['embedding']

def create_context(question, df, max_len=1800, size="ada"):
    question_embedding = get_embeddings(question)
    df['similarity'] = df['embeddings'].apply(lambda x: cosine_similarity([question_embedding], [x])[0][0])
    df = df.sort_values('similarity', ascending=False)
    context = ""
    for _, row in df.iterrows():
        context += row['text'] + "\n"
        if len(context) > max_len:
            break
    return context

def answer_question(df, question, max_len=1800, size="ada", max_tokens=150, stop_sequence=None):
    context = create_context(question, df, max_len=max_len, size=size)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Answer the question based on the context below, and if the question can't be answered based on the context, say 'I don't know'"},
            {"role": "user", "content": f"Context: {context}\n\n---\n\nQuestion: {question}\nAnswer:"}
        ],
        max_tokens=max_tokens,
        stop=stop_sequence,
    )
    return response.choices[0].message['content'].strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdfFile' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['pdfFile']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        global df
        text = extract_text_from_pdf(file_path)
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
        embeddings = [get_embeddings(chunk) for chunk in chunks]
        df = pd.DataFrame({'text': chunks, 'embeddings': embeddings})
        return jsonify({'message': 'File uploaded successfully'}), 200
    return jsonify({'error': 'File not allowed'}), 400

@app.route('/ask', methods=['POST'])
def ask_question_route():
    data = request.get_json()
    question = data['question']
    answer = answer_question(df, question)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
