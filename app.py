import streamlit as st
import openai
import os
import requests
import json
from PIL import Image
from io import BytesIO
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import gpt_prompt

openai.api_key = os.getenv('OPENAI_API_KEY')
mj_api_key = os.getenv('MJ_API_KEY')

@st.cache_data
def imagine(prompt):
    headers = {
    'Authorization': f'Bearer {mj_api_key}',
    'Content-Type': 'application/json'
    }

    url = "https://api.thenextleg.io/v2/imagine"

    payload_image = json.dumps({
    "msg": prompt,
    "ref": "",
    "webhookOverride": "", 
    "ignorePrefilter": "false"
    })

    def check_task_status(url):
        while True:
            response_result = requests.request("GET", url, headers=headers)
            if response_result.status_code == 200:
                json_response = json.loads(response_result.text)
                progress = json_response['progress']
                if progress == 100:
                    return json_response["response"]['imageUrl']
            else:
                st.write(f"Request failed, status code: {response_result.status_code}")
            time.sleep(3)

    attempts = 0
    max_attempts = 3
    while attempts <= max_attempts:
        time.sleep(3)
        messageId = None
        response_image = requests.request("POST", url, headers=headers, data=payload_image)
        if response_image.status_code == 200:
            messageId = response_image.json().get('messageId')

        url_with_id = f"https://api.thenextleg.io/v2/message/{messageId}?expireMins=2"
        
        if messageId:
            img_url = check_task_status(url_with_id)
            if img_url is not None and img_url != '':
                return img_url
            else:
                attempts += 1
    raise ValueError("Unable to get valid image URL after multiple attempts")

# get session state
if 'init_prompt' not in st.session_state:
    st.session_state.init_prompt = ''
if 'prompts' not in st.session_state:
    st.session_state.prompts = []
if 'prompt_history' not in st.session_state:
    st.session_state.prompt_history = []
if 'images' not in st.session_state:
    st.session_state.images = []
if 'image_history' not in st.session_state:
    st.session_state.image_history = []
if 'selection_history' not in st.session_state:
    st.session_state.selection_history = []
if 'selected_images' not in st.session_state:
    st.session_state.selected_images = []
if 'scores' not in st.session_state:
    st.session_state.scores = []
if 'round_count' not in st.session_state:
    st.session_state.round_count = 0
if 'keyword_mat' not in st.session_state:
    st.session_state.keyword_mat = None

st.title("Genjourney:dna:")

# choose the mj mode
option = st.radio('**Choose a Midjourney mode:**', ('Midjourney Model V5.2', 'Niji Model V5'))

# input init prompt and generate prompts of generation 0
st.session_state.init_prompt = st.text_input("**Enter your initial prompt**", value=st.session_state.init_prompt)

if st.button("**Generate prompts & images**"):

    prompt_mat, keyword_mat = gpt_prompt.generate(st.session_state['init_prompt'], 5)
    st.session_state.keyword_mat = keyword_mat
    st.session_state.prompts = prompt_mat

if np.size(st.session_state.prompts) > 0:
    # show the lastest images
    st.markdown("# Current Images")

    image_list = []
    for i in range(len(st.session_state.prompts)):
        prompt = gpt_prompt.list2str(st.session_state.prompts[i], option)
        st.write(i+1, prompt)
        img = imagine(prompt)
        st.image(img, caption=prompt)
        image_list.append(img)
    st.session_state.images = image_list

    # # multi-thread
    # def get_image(prompt):
    #     img = imagine(prompt)
    #     return img, prompt

    # # results = []
    # # with ThreadPoolExecutor(max_workers=5) as executor:
    # #     futures = [executor.submit(get_image, gpt_prompt.list2str(prompt, option)) for prompt in st.session_state.prompts]
    # #     progress_bar = st.progress(0)
    # #     for i, future in enumerate(as_completed(futures)):
    # #         results.append(future.result())
    # #         progress_bar.progress((i+1) / len(futures))

    # # for i, (img, prompt) in enumerate(results, start=1):
    # #     st.image(img, caption=f"{i}. {prompt}")

    # with ThreadPoolExecutor(max_workers=5) as executor:
    #     futures = [executor.submit(get_image, gpt_prompt.list2str(prompt, option)) for prompt in st.session_state.prompts]
    #     progress_bar = st.progress(0)
    #     results = []
    #     for i, future in enumerate(as_completed(futures)):
    #         img, prompt = future.result()
    #         results.append((img, prompt))
    #         progress_bar.progress((i + 1) / len(futures))
    #     progress_bar.progress(1.0)

    # image_list = []
    # for i, (img, prompt) in enumerate(results, start=1):
    #     st.write(f"{i}. {prompt}")
    #     st.image(img, caption=prompt)
    #     image_list.append(img)

    # st.session_state.images = image_list

    with st.form(key='my_form'):
        # let user to choose two prompts as parent prompts
        st.session_state.selected_images = st.multiselect('Select two prompts as parent prompts', range(1, 6), key=f"select_{st.session_state.round_count}")
        
        # let user to rate the art styles
        # if st.session_state.selected_images and len(st.session_state.selected_images) == 2:
        if st.session_state.selected_images:
            if len(st.session_state.selected_images) != 2:
                st.warning('Please select exactly two images and set scores for them.')
            else:
                subject_rate = st.slider('rate the subject', min_value=0, max_value=10, value=5, key=f"slider_subject_{st.session_state.round_count}_{i}")
                style_rate = st.slider('rate the style', min_value=0, max_value=10, value=5, key=f"slider_style_{st.session_state.round_count}_{i}")
                color_rate = st.slider('rate the color', min_value=0, max_value=10, value=5, key=f"slider_color_{st.session_state.round_count}_{i}")
                angle_rate = st.slider('rate the angle', min_value=0, max_value=10, value=5, key=f"slider_angle_{st.session_state.round_count}_{i}")
                light_rate = st.slider('rate the light', min_value=0, max_value=10, value=5, key=f"slider_light_{st.session_state.round_count}_{i}")
                renderer_rate = st.slider('rate the renderer', min_value=0, max_value=10, value=5, key=f"slider_renderer_{st.session_state.round_count}_{i}")
                rate_list = [subject_rate, style_rate, color_rate, angle_rate, light_rate, renderer_rate]
                st.session_state.scores = rate_list
        
        # submit button
        submit_button = st.form_submit_button(label='Submit for Next Generation')

    if submit_button:
        if len(st.session_state.selected_images) != 2:
            st.warning('Please select exactly two images and set scores for them.')
        else:
            # store history
            st.session_state.prompt_history.append(st.session_state.prompts)
            st.session_state.image_history.append(st.session_state.images)
            st.session_state.selection_history.append(st.session_state.selected_images)

            # generate prompts of next generation
            prompt_A = st.session_state.prompts[st.session_state.selected_images[0]-1]
            prompt_B = st.session_state.prompts[st.session_state.selected_images[1]-1]
            st.session_state.prompts = gpt_prompt.genetic(prompt_A, prompt_B, st.session_state.scores, st.session_state.keyword_mat)

            # increase round count
            st.session_state.round_count += 1

            # clear selection and scores
            st.session_state.selected_images = []
            st.session_state.scores = []

    # show history and selection on sidebar
    if st.session_state.image_history:
        st.sidebar.markdown("# History")
        for i, (past_images, selected) in enumerate(zip(st.session_state.image_history, st.session_state.selection_history)):
            st.sidebar.markdown(f"## Generation {i}")
            for idx, img in enumerate(past_images):
                prompt = gpt_prompt.list2str(st.session_state.prompt_history[i][idx], option)
                caption = prompt + (f" - Selected" if (idx+1) in selected else "")
                st.sidebar.image(img, caption=caption)