'''
Created on Nov 25, 2021

@author: immanueltrummer
'''
import json
import requests
import streamlit as st

st.set_page_config(page_title='Virtual Teaching Assistant')

@st.cache(allow_output_mutation=True)
def generate_answer(question):
    """ Query endpoint for question answering.
    
    Args:
        question: the question to answer
    
    Returns:
        dictionary with answer properties
    """
    http_r = requests.get(answer_url, params={'question':question})
    r_dict = json.loads(http_r.text)
    return r_dict

@st.cache(allow_output_mutation=True)
def register_feedback(feedback):
    """ Register feedback in the database. 
    
    Args:
        feedback: dictionary with feedback
    """
    http_r = requests.get(feedback_url, params=feedback)
    return http_r.text

answer_url = st.secrets['answer_url']
feedback_url = st.secrets['feedback_url']
correct_password = st.secrets['password']

password = st.text_input('Enter password:', type='password')
if password == correct_password:

    st.header('"Virtual Teaching Assistant" for the Database Lecture')
    
    st.markdown('''
        This tool answers natural language questions about the course material 
        taken from [the database lecture](http://www.databaselecture.com). Answers 
        may be inaccurate and should be **verified** using **alternative** sources. 
        The tool returns links to video material that can be used for verification 
        and further details.
        
        Example questions:
        - Explain this SQL query: SELECT Avg(age) FROM Customers GROUP BY zip_code
        - What is the second rule of write-ahead logging? 
        - What is a strict schedule?
        ''')
    
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
                
                approved = st.button('👍')
                improved = st.text_input('Suggest better answer:', max_chars=200)
                if approved:
                    register_feedback({
                        'approved':'True', 'question':question, 'answer':answer})
                if improved:
                    register_feedback({
                        'improved':improved, 'question':question, 'answer':answer})