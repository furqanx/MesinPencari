import re
import os
import subprocess
from flask import Flask, render_template, request

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    selected_backend = request.form['backend']

    if selected_backend == 'c_code':
        status, backend, search_time_seconds, keywords, number_of_hits, file_names, scores = run_c_code_backend(query)
    elif selected_backend == 'swish_e':
        status, backend, search_time_seconds, number_of_hits, paths, filenames = run_swish_e_backend(query)
    else:
        return "Backend tidak valid"

    if status:
        if backend == "c-code":
            keywords_number_of_hits_zipped_data = zip(keywords, number_of_hits)
            file_names_scores_zipped_data = zip(file_names, scores)

            return render_template('index.html', query=query, status=status, backend=backend,
                                search_time_seconds=search_time_seconds, 
                                keywords_number_of_hits_zipped_data=keywords_number_of_hits_zipped_data,
                                file_names_scores_zipped_data=file_names_scores_zipped_data)
        elif backend == "swish-e":
            paths_filenames_zipped_data = zip(paths, filenames)

            return render_template('index.html', query=query, status=status, backend=backend,
                                search_time_seconds=search_time_seconds, 
                                number_of_hits=number_of_hits,  
                                paths_filenames_zipped_data=paths_filenames_zipped_data)
    else:
        return render_template('index.html', query=query, status=status)


def run_c_code_backend(query):
    # Implementasi untuk menjalankan backend C-code
    backend = "c-code"

    current_directory = os.getcwd()
    input_text = query
    command = f"./querydb '{input_text}'"

    os.chdir("rank-c")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    os.chdir(current_directory)

    search_results = result.stdout.strip().split('\n')

    # extracting outputs
    lines = search_results

    if len(lines) > 4 :
        status = True
    
        # extracting search times
        time_pattern = re.compile(r"#Time required: (\d+\.\d+) mseconds")
        time_result = [float(match.group(1)) for line in lines if (match := time_pattern.match(line))]
        time_in_seconds = time_result[0] / 1000
        search_time_seconds = time_in_seconds

        # extracting query and number of hits
        keywords = []
        number_of_hits = []

        pattern = re.compile(r"#Word \['(\w+)'\], fw \(num of doc containing the word\) = (\d+\.\d+)")
        query_number_of_hits_matches = [pattern.match(line) for line in lines if line.startswith("#Word")]  # tuple inside list

        for match in query_number_of_hits_matches:
            if match:
                keyword, hit = match.groups()
                keywords.append(keyword)
                number_of_hits.append(float(hit))

        # extracting file names and it's score value
        pattern = re.compile(r"\d+\s+(\S+)\s+(\d+\.\d+)")
        file_value_matches = [(match.group(1), float(match.group(2))) for line in lines if (match := pattern.match(line))]  # tuple inside list

        file_names = [file_value[0] for file_value in file_value_matches]
        scores = [file_value[1] for file_value in file_value_matches]

        return status, backend, search_time_seconds, keywords, number_of_hits, file_names, scores
    else:
        status = False

        return status, backend, None, None, None, None, None

def run_swish_e_backend(query):
    # Implementasi untuk menjalankan backend Swish-e
    backend = "swish-e"

    result = subprocess.run(['swish-e', '-w', query, '-f', 'swish-e/result.index'], capture_output=True, text=True)
    search_results = result.stdout.strip().split('\n')

    if len(search_results) > 5:
        status = True

        # extracting search time
        search_time_string = search_results[4]
        search_time_string = search_time_string.replace(',', '.')
        pattern = re.compile(r'Search time: (\d+\.\d{3}) seconds')
        match = pattern.search(search_time_string)
        search_time_seconds = float(match.group(1))

        # extracting number of hits
        hits_string = search_results[3]
        pattern = re.compile(r'Number of hits: (\d+)')
        match = pattern.search(hits_string)
        number_of_hits = int(match.group(1))

        # extracting file paths
        document_strings = search_results[6:] 
        pattern = re.compile(r'\d+ (\S+) "(\S+)" \d+')

        paths = []
        filenames = []

        matches = [pattern.match(line) for line in document_strings if pattern.match(line)]
        for match in matches:
            path = match.group(1)
            filename = match.group(2)
            paths.append(path)
            filenames.append(filename)
        
        return status, backend, search_time_seconds, number_of_hits, paths, filenames
    else:
        status = False

        return status, backend, None, None, None, None

@app.route('/document/<filename>')
def show_document(filename):
    document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    with open(document_path, 'r', encoding='utf-8') as file:
        title = file.readline().strip()
        content = file.read()

    return render_template('document.html', filename=filename, title=title, content=content)

if __name__ == '__main__':
    app.run(debug=True)
