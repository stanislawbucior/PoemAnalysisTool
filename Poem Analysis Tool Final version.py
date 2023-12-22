import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from openai import OpenAI
import os
from PyPDF2 import PdfReader
import json
import pandas as pd
import time

# Initialize the OpenAI client
client = OpenAI(
    api_key=input("Enter the openai api key: ")  # Enter the API key
)

# Export text from pdf file into a string
def extract_text_from_pdf(pdf_file_path):
    text_content = ""
    with open(pdf_file_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"
    return text_content

def send_message(thread_id, user_message):
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )
    return message

# Function to check whether the analysis by api is completed
def wait_on_run(run_id, thread_id):
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id,
        )
        if run.status == "completed":
            return run
        elif run.status in ["failed", "cancelled"]:
            raise Exception(f"Run failed or was cancelled: {run.status}")
        time.sleep(1)

def run_assistant_and_get_response(assistant_id, thread_id, last_response_id=None):
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    run = wait_on_run(run.id, thread_id)

    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )
    answers = []
    latest_response_id = last_response_id
    for message in messages.data:
        if message.role == "assistant" and (last_response_id is None or message.id > last_response_id):
            try:
                answer = message.content[0].text.value
                answers.append(answer)
            except AttributeError:
                print("No reply")
            latest_response_id = message.id
            
    return latest_response_id, answers

# Function to display DataFrame in a Treeview widget
def display_dataframe_in_treeview(df):
    # Create a new Toplevel window
    top_level = tk.Toplevel(window)
    top_level.title("DataFrame Output")
    
    # Create the Treeview widget with the correct column identifiers
    columns = list(df.columns)
    tree = ttk.Treeview(top_level, columns=columns, show='headings')
    
    # Generate the headings
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="w")
    
    # Insert the data into the Treeview
    for index, row in df.iterrows():
        # Ensure that the values are passed in the same order as the columns
        tree.insert('', 'end', values=row[columns].tolist())
    
    # Add scrollbars
    scrollbar_vertical = ttk.Scrollbar(top_level, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_vertical.set)
    scrollbar_vertical.pack(side='right', fill='y')

    scrollbar_horizontal = ttk.Scrollbar(top_level, orient='horizontal', command=tree.xview)
    tree.configure(xscrollcommand=scrollbar_horizontal.set)
    scrollbar_horizontal.pack(side='bottom', fill='x')

    tree.pack(expand=True, fill='both')

# Function to...
def process_analysis_results(analysis_result):
    analysis_output = json.loads(analysis_result)
    if 'poemAnalysisOutput' in analysis_output:
        poem_data = analysis_output['poemAnalysisOutput']
        # If 'analysis' is a nested dictionary, we normalize it first 
        if 'analysis' in poem_data:
            analysis_flat = pd.json_normalize(poem_data['analysis'])
            poem_data.update(analysis_flat.to_dict(orient='records')[0])
            del poem_data['analysis']
        
        df = pd.DataFrame([poem_data])  # The data is in a dictionary, so let's make a list out of it
        display_dataframe_in_treeview(df)
    else:
        messagebox.showinfo("Result", "No analysis found in the result.")

# Function allowing to select a pdf file
def select_pdf_file():
    file_path = filedialog.askopenfilename(
        title="Select a PDF file",
        filetypes=[("PDF files", "*.pdf")]
    )
    if file_path:
        entry_pdf_path.delete(0, tk.END)
        entry_pdf_path.insert(0, file_path)

def process_text(text):
    try:
        existing_assistant_id = "asst_E3qfm6X0yQam3oNuHPy7Zq79"
        thread = client.beta.threads.create()
        send_message(thread.id, text)
        last_response_id, answers = run_assistant_and_get_response(existing_assistant_id, thread.id)

        if answers:
            # Debug: Print the answer to check if it's valid JSON
            print("Received answer:", answers[0])
            try:
                process_analysis_results(answers[0])
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"An error occurred in JSON parsing: {e}")
        else:
            messagebox.showinfo("Result", "No answers were received for analysis.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")



# GUI Functions
def on_input_choice():
    if input_choice.get() == 'PDF':
        text_input.pack_forget()
        entry_pdf_path.pack(padx=10, pady=5)
        button_select_pdf.pack(pady=5)
        button_analyze.pack(pady=5)
    elif input_choice.get() == 'Text':
        entry_pdf_path.pack_forget()
        button_select_pdf.pack_forget()
        text_input.pack(padx=10, pady=5)
        button_analyze.pack(pady=5)

def analyze_pdf():
    pdf_file_path = entry_pdf_path.get()
    if not os.path.isfile(pdf_file_path):
        messagebox.showerror("Error", "The specified file was not found.")
        return
    
    pdf_text = extract_text_from_pdf(pdf_file_path)
    process_text(pdf_text)

# Function to get the text of poem for the analysis
def analyze_text():
    user_text = text_input.get('1.0', tk.END).strip()
    if not user_text:
        messagebox.showerror("Error", "No text to analyze.")
        return
    process_text(user_text)

# GUI Setup
window = tk.Tk()
window.title("Poem Analysis Tool")

# Variable to store the input choice
input_choice = tk.StringVar(value='PDF')

# Radio buttons for input choice
radio_pdf = tk.Radiobutton(window, text="Upload PDF", variable=input_choice, value='PDF', command=on_input_choice)
radio_text = tk.Radiobutton(window, text="Enter Text", variable=input_choice, value='Text', command=on_input_choice)
radio_pdf.pack(anchor='w', padx=10, pady=5)
radio_text.pack(anchor='w', padx=10, pady=5)

# PDF path entry
entry_pdf_path = tk.Entry(window, width=50)

# Select PDF button
button_select_pdf = tk.Button(window, text="Select PDF", command=select_pdf_file)

# Text input area for direct text entry
text_input = scrolledtext.ScrolledText(window, height=10)

# Analyze button for both PDF and text input
button_analyze = tk.Button(window, text="Analyze", command=lambda: analyze_pdf() if input_choice.get() == 'PDF' else analyze_text())

# Initial input choice setup
on_input_choice()

window.mainloop()