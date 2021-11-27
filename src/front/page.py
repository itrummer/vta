'''
Created on Nov 25, 2021

@author: immanueltrummer
'''
import json
import random
import requests
import streamlit as st
import string
import time

st.set_page_config(
    page_title='Virtual Teaching Assistant',
    layout='wide')

@st.cache(suppress_st_warning=True)
def add_videos(evidence):
    """ Adds related videos to sidebar, based on evidence.
    
    Args:
        evidence: pieces of evidence supporting generated answer
    """
    st.write(evidence)
    evidence.sort(key=lambda e:e['score'], reverse=True)
    if evidence:
        video_ids = set()
        video_urls = []
        max_nr_videos = min(len(evidence), 3)
        for e in evidence[0:max_nr_videos]:
            meta_data = e['metadata']
            video_id = meta_data['video']
            if video_id not in video_ids:
                start_s = int(meta_data['start'])
                y_url = 'https://www.youtube.com/watch'
                video_url = f'{y_url}?v={video_id}&t={start_s}s'
                video_ids.add(video_id)
                video_urls.append(video_url)

        st.sidebar.header('Related Lecture Videos')
        for v in video_urls:
            st.sidebar.video(v)

def check_rate():
    """ Checks rate of query generation.
    
    Returns:
        true iff the query rate is acceptable
    """
    cur_s = time.time()
    init_s = st.session_state['init_s']
    elapsed_s = cur_s - init_s
    query_nr = st.session_state['query_nr']
    if query_nr == 0:
        return True
    elif elapsed_s / query_nr < 10:
        return False
    else:
        return True   

@st.cache(allow_output_mutation=True)
def generate_answer(question):
    """ Query endpoint for question answering.
    
    Args:
        question: the question to answer
    
    Returns:
        dictionary with answer properties
    """
    if not check_rate():
        return {'error':True, 'answer':'Error - reached query rate limits.'}
    else:
        http_r = requests.get(st.session_state['answer_url'], params={
            'question':question, 'user_id':st.session_state['user_id']})
        r_dict = json.loads(http_r.text)
        st.session_state['query_nr'] = st.session_state['query_nr'] + 1
        return r_dict

def generate_id(length):
    """ Generate random ID string with given length.
    
    Args:
        length: length of ID string
    
    Returns:
        randomly generated ID string
    """
    return ''.join(random.choice(string.ascii_letters) for _ in range(length)) 

@st.cache(allow_output_mutation=True)
def login(password):
    """ Verify password and return URLs of endpoints if successful. 
    
    Args:
        password: user-provided password
    
    Returns:
        dictionary containing error message or URLs
    """
    http_r = requests.get(
        'https://us-central1-dbvta-9bf4b.cloudfunctions.net/login', 
        params={'password':password})
    return json.loads(http_r.text)

@st.cache(allow_output_mutation=True)
def register_feedback(feedback):
    """ Register feedback in the database. 
    
    Args:
        feedback: dictionary with feedback
    """
    feedback['user_id'] = st.session_state['user_id']
    http_r = requests.get(st.session_state['feedback_url'], params=feedback)
    return http_r.text

# answer_url = st.secrets['answer_url']
# feedback_url = st.secrets['feedback_url']
# correct_password = st.secrets['password']

if 'user_id' not in st.session_state:
    st.session_state['user_id'] = generate_id(48)
    st.session_state['init_s'] = time.time()
    st.session_state['query_nr'] = 0

logged_in = False
password = st.text_input('Enter password:', type='password')
if password:
    r_dict = login(password)
    if 'error' in r_dict:
        st.error(r_dict['error'])
    else:
        st.session_state['answer_url'] = r_dict['answer_url']
        st.session_state['feedback_url'] = r_dict['feedback_url']
        logged_in = True

if logged_in:
    st.header('Ask Questions about Database Systems')
    st.markdown('''
        This tool answers natural language questions about the course material 
        taken from [the database lecture](http://www.databaselecture.com). Answers 
        may be inaccurate and should be **verified** using **alternative** sources. 
        The tool returns links to video material that can be used for verification 
        and further details.
        
        Example questions:
        - Explain this SQL query: SELECT Avg(age) FROM Customers GROUP BY zip_code
        - What does the rectangle represent in ER diagrams?
        - What is a strict schedule? 
        ''')
    #- What is the second rule of write-ahead logging?
    
    question = st.text_input('Enter your question:', max_chars=200)
    
    if question:
        r_dict = generate_answer(question)
        if not ('answer' in r_dict):
            st.error('Failed to obtain answer from server. Please retry later!')
        else:
            answer = r_dict['answer']
            if r_dict['error']:
                st.error(answer)
            else:
                st.info(f'**Answer**: {answer}')
                
                if 'result' in r_dict:
                    result = r_dict['result']
                
                    if 'selected_documents' in result:
                        evidence = result['selected_documents']
                        add_videos(evidence)
                
                approved = st.button('👍')
                improved = st.text_input('Suggest better answer:', max_chars=200)
                if approved:
                    register_feedback({
                        'approved':'True', 'question':question, 'answer':answer})
                if improved:
                    register_feedback({
                        'improved':improved, 'question':question, 'answer':answer})