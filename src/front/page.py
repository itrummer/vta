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

retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)

def add_videos(evidence):
    """ Adds related videos to sidebar, based on evidence.
    
    Args:
        evidence: pieces of evidence supporting generated answer
    """
    evidence.sort(key=lambda e:e['score'], reverse=True)
    if evidence:
        video_ids = set()
        video_snippets = []
        max_nr_videos = min(len(evidence), 3)
        for e in evidence[0:max_nr_videos]:
            meta_data = e['metadata']
            video_id = meta_data['video']
            if video_id not in video_ids:
                start_s = int(meta_data['start'])
                y_url = 'https://www.youtube.com/watch'
                # video_url = f'{y_url}?v={video_id}&t={start_s}s'
                video_url = f'{y_url}?v={video_id}'
                video_ids.add(video_id)
                video_snippets.append((video_url, start_s))
        
        exp = st.expander(label='Click for Related Lecture Videos')
        nr_videos = len(video_snippets)
        cols = exp.columns(nr_videos)
        for c, (v, s) in zip(cols, video_snippets):
            c.video(v, start_time=s)

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
        with requests.Session() as s:
            s.mount('http://', retry_adapter)
            s.mount('https://', retry_adapter)
            http_r = s.get(
                'https://us-central1-dbvta-9bf4b.cloudfunctions.net/vta_answer',
                timeout=6, params={
                    'question':question, 'user_id':st.session_state['user_id']}
                )
            if http_r.status_code == 200:
                r_dict = json.loads(http_r.text)
                st.session_state['query_nr'] = st.session_state['query_nr'] + 1
                return r_dict
            else:
                return {}

def generate_id(length):
    """ Generate random ID string with given length.
    
    Args:
        length: length of ID string
    
    Returns:
        randomly generated ID string
    """
    return ''.join(random.choice(string.ascii_letters) for _ in range(length)) 

# @st.cache(allow_output_mutation=True)
# def login(password):
    # """ Verify password and return URLs of endpoints if successful. 
    #
    # Args:
        # password: user-provided password
        #
    # Returns:
        # dictionary containing error message or URLs
    # """
    # with requests.Session() as s:
        # s.mount('http://', retry_adapter)
        # s.mount('https://', retry_adapter)
        # http_r = s.get(
            # 'https://us-central1-dbvta-9bf4b.cloudfunctions.net/login', 
            # params={'password':password}, timeout=3)
        # if http_r.status_code == 200:
            # return json.loads(http_r.text)
        # else:
            # st.error('Error - connection to server failed. Please retry later.')
            # return {}

@st.cache(suppress_st_warning=True)
def register_feedback(feedback):
    """ Register feedback in the database. 
    
    Args:
        feedback: dictionary with feedback
    """
    feedback['user_id'] = st.session_state['user_id']
    feedback_url = 'https://us-central1-dbvta-9bf4b.cloudfunctions.net/register_feedback'
    with requests.Session() as s:
        s.mount('http://', retry_adapter)
        s.mount('https://', retry_adapter)
        s.get(feedback_url, params=feedback, timeout=5)
        st.success('Your feedback was sent.')

if 'user_id' not in st.session_state:
    st.session_state['user_id'] = generate_id(48)
    st.session_state['init_s'] = time.time()
    st.session_state['query_nr'] = 0
#
# logged_in = False
# password = st.text_input('Enter password:', type='password')
# if password:
    # r_dict = login(password)
    # if 'error' in r_dict:
        # st.error(r_dict['error'])
    # else:
        # st.session_state['answer_url'] = r_dict['answer_url']
        # st.session_state['feedback_url'] = r_dict['feedback_url']
        # logged_in = True

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
            send_improved = st.button('Send Suggestion')
            if approved:
                register_feedback({
                    'approved':'True', 'question':question, 'answer':answer})
            if send_improved:
                if improved:
                    register_feedback({'improved':improved, 
                                       'question':question, 'answer':answer})
                else:
                    st.error('Error - please suggest an improved answer.')