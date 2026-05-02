import os
import csv
import streamlit as st
import nltk
import re
nltk.download('stopwords', quiet=True)
nlp = None

import pandas as pd
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import LAParams
import base64, random
import time, datetime

import io, random
from streamlit_tags import st_tags
from PIL import Image
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import yt_dlp
import plotly.express as px
# SQLite connection
import sqlite3
connection = sqlite3.connect("resume.db", check_same_thread=False)
cursor = connection.cursor()

def load_academic_dataset():
    if os.path.exists("resume_dataset.csv"):
        df = pd.read_csv(
            "resume_dataset.csv",
            engine="python"
        )

        return df
    else:
        return pd.DataFrame()

def fetch_yt_video(link):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        return info.get("title", "Unknown Title")


def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    # href = f'<a href="data:file/csv;base64,{b64}">Download Report</a>'
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href


def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh,
                                      caching=True,
                                      check_extractable=True):
            page_interpreter.process_page(page)
            print(page)
        text = fake_file_handle.getvalue()

    # close open handles
    converter.close()
    fake_file_handle.close()
    return text


def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    # pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf">'
    pdf_display = f"""
    <iframe 
        src="data:application/pdf;base64,{base64_pdf}"
        width="700" 
        height="900" 
        type="application/pdf">
    </iframe>
    """

    st.markdown(pdf_display, unsafe_allow_html=True)


def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break

    connection = None
    cursor = None


def insert_data(name, email, res_score, timestamp,
                no_of_pages, reco_field, cand_level,
                skills, recommended_skills, courses):

    insert_sql = """
    INSERT INTO user_data
    (Name, Email_ID, resume_score, Timestamp, Page_no,
     Predicted_Field, User_level, Actual_skills,
     Recommended_skills, Recommended_courses)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    rec_values = (
        name, email, res_score, timestamp,
        no_of_pages, reco_field, cand_level,
        skills, recommended_skills, courses
    )

    cursor.execute(insert_sql, rec_values)
    connection.commit()





st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon='./Logo/SRA_Logo.ico',
)
def save_to_csv(name, email, skills, pages, level, field):
    file_exists = os.path.exists("resume_dataset.csv")

    if isinstance(skills, list):
        skills = "|".join(skills)

    with open("resume_dataset.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "name", "email", "skills",
                "no_of_pages", "experience_level", "job_field"
            ])
        writer.writerow([
            name, email, skills, pages, level, field
        ])

def run():

    st.title("Smart Resume Analyser")
    reco_field = ""
    cand_level = ""
    rec_course = []
    recommended_skills = []


    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    # link = '[©Developed by Spidy20](http://github.com/spidy20)'
    # st.sidebar.markdown(link, unsafe_allow_html=True)
    import os
    from PIL import Image
    logo_path = os.path.join("Logo", "SRA_Logo.jpg")

    if os.path.exists(logo_path):
        img = Image.open(logo_path)
        img = img.resize((250, 250))
        st.image(img)
    else:
        st.warning("Logo image not found")




    # Create table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT,
        Email_ID TEXT,
        resume_score TEXT,
        Timestamp TEXT,
        Page_no TEXT,
        Predicted_Field TEXT,
        User_level TEXT,
        Actual_skills TEXT,
        Recommended_skills TEXT,
        Recommended_courses TEXT
    )
    """)
    connection.commit()
    if choice == 'Normal User':
        # st.markdown('''<h4 style='text-align: left; color: #d73b5c;'>* Upload your resume, and get smart recommendation based on it."</h4>''',
        #             unsafe_allow_html=True)
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        if pdf_file is not None:

            save_image_path = './Uploaded_Resumes/' + pdf_file.name

            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            st.subheader("📄 Uploaded Resume Preview")
            show_pdf(save_image_path)
            # ✅ Extract text
            resume_text = pdf_reader(save_image_path)


            # ✅ Extract email
            email = re.findall(r'\S+@\S+', resume_text)
            email = email[0] if email else "Not Found"

            # ✅ Extract phone
            phone = re.findall(r'\b\d{10}\b', resume_text)
            phone = phone[0] if phone else "Not Found"

            # ✅ Extract name (simple method)
            name = resume_text.split('\n')[0]


            # ✅ Skills (basic extraction)
            skills = list(set(re.findall(
                r'\b(python|java|sql|react|django|flask|machine learning|ai|html|css|javascript)\b',
                resume_text.lower()
            )))
            # Page count (simple OR use function)
            no_of_pages = 1

            resume_data = {
                "name": name,
                "email": email,
                "mobile_number": phone,
                "no_of_pages": no_of_pages,
                "skills": skills
            }

            resume_text = resume_text.lower()
            resume_score = 0
            resume_data["skills"] = re.findall(
         r'\b(?:python|java|sql|react|django|flask|ml|ai)\b',
                resume_text
            )

            sections = {
                ('objective', 'career objective'): 10,
                ('education', 'educational'): 15,
                ('experience', 'work experience'): 20,
                ('skills', 'technical skills'): 20,
                ('projects', 'academic projects'): 15,
                ('certification', 'certifications'): 10,
                ('achievement', 'achievements'): 10
            }

            for keys, mark in sections.items():
                if any(k in resume_text for k in keys):
                    resume_score += mark
                    st.markdown(
                        f"<h4 style='color:#1ed760;'>[+] {keys[0].title()} section found (+{mark})</h4>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<h4 style='color:#fabc10;'>[-] Consider adding {keys[0].title()} section</h4>",
                        unsafe_allow_html=True
                    )

                # Maximum score cap
                if resume_score > 100:
                    resume_score = 100

                st.header("**Resume Analysis**")
                st.success("Hello " + resume_data['name'])
                st.subheader("**Your Basic info**")
                try:
                    st.text('Name: ' + resume_data['name'])
                    st.text('Email: ' + resume_data['email'])
                    st.text('Contact: ' + resume_data['mobile_number'])
                    st.text('Resume pages: ' + str(resume_data['no_of_pages']))
                except:
                    pass
                cand_level = ''
                if resume_data['no_of_pages'] == 1:
                    cand_level = "Fresher"
                    st.warning("You are looking Fresher.")
                elif resume_data['no_of_pages'] == 2:
                    cand_level = "Intermediate"
                    st.success("You are at intermediate level!")
                else:
                    cand_level = "Experienced"
                    st.info("You are at experienced level!")

                st.subheader("**Skills Recommendation💡**")

                st.write("### 🛠 Detected Skills:")

                if resume_data['skills']:
                    for skill in resume_data['skills']:
                        st.success(skill)
                    st_tags(
                        label='### Skills that you have',
                        text='Detected from your resume',
                        value=resume_data['skills'],
                        key=f"skills_{pdf_file.name}"
                    )
                else:
                    st.warning("No skills detected in your resume")
                ##  recommendation
                ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep Learning', 'flask',
                              'streamlit']
                web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress',
                               'javascript', 'angular js', 'c#', 'flask']
                android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes',
                                'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator',
                                'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro',
                                'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp',
                                'user research', 'user experience']

                recommended_skills = []
                reco_field = ''
                rec_course = ''

                ## Courses recommendation
                skills_list = resume_data.get('skills', []) or []

                for i in skills_list:
                    ## Data science recommendation
                    if i.lower() in ds_keyword:
                        print(i.lower())
                        reco_field = 'Data Science'
                        st.success("** Our analysis says you are looking for Data Science Jobs.**")
                        recommended_skills = [
                            'Data Visualization', 'Predictive Analysis', 'Statistical Modeling',
                            'Data Mining', 'Clustering & Classification', 'Data Analytics',
                            'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras',
                            'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', 'Flask',
                            'Streamlit'
                        ]

                        recommended_keywords = st_tags(
                            label='### Recommended skills for you.',
                            text='Recommended skills generated from System',
                            value=recommended_skills,
                            key='2'
                        )
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(ds_course)
                        break

                    ## Web development recommendation
                    elif i.lower() in web_keyword:
                        print(i.lower())
                        reco_field = 'Web Development'
                        st.success("** Our analysis says you are looking for Web Development Jobs **")
                        recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento',
                                              'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='3')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(web_course)
                        break

                    ## Android App Development
                    elif i.lower() in android_keyword:
                        print(i.lower())
                        reco_field = 'Android Development'
                        st.success("** Our analysis says you are looking for Android App Development Jobs **")
                        recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 'Java',
                                              'Kivy', 'GIT', 'SDK', 'SQLite']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='4')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(android_course)
                        break

                    ## IOS App Development
                    elif i.lower() in ios_keyword:
                        print(i.lower())
                        reco_field = 'IOS Development'
                        st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                        recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 'Xcode',
                                              'Objective-C', 'SQLite', 'Plist', 'StoreKit', "UI-Kit", 'AV Foundation',
                                              'Auto-Layout']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='5')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(ios_course)
                        break

                    ## Ui-UX Recommendation
                    elif i.lower() in uiux_keyword:
                        print(i.lower())
                        reco_field = 'UI-UX Development'
                        st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                        recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 'Balsamiq',
                                              'Prototyping', 'Wireframes', 'Storyframes', 'Adobe Photoshop', 'Editing',
                                              'Illustrator', 'After Effects', 'Premier Pro', 'Indesign', 'Wireframe',
                                              'Solid', 'Grasp', 'User Research']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='6')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        rec_course = course_recommender(uiux_course)
                        break

                #
                ## Insert into table
                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date + '_' + cur_time)

                ### Resume writing recommendation



                from pdfminer.pdfpage import PDFPage

                def get_pdf_page_count(file_path):
                    with open(file_path, "rb") as f:
                        return len(list(PDFPage.get_pages(f)))

                resume_data["no_of_pages"] = get_pdf_page_count(save_image_path)
                resume_text = resume_text.lower()
                resume_score = 0

                sections = {
                    ('objective', 'career objective'): 10,
                    ('education', 'educational'): 15,
                    ('experience', 'work experience'): 20,
                    ('skills', 'technical skills'): 20,
                    ('projects', 'academic projects'): 15,
                    ('certification', 'certifications'): 10,
                    ('achievement', 'achievements'): 10
                }

                st.subheader("**Resume Tips & Ideas💡**")

                for keys, mark in sections.items():
                    if any(k in resume_text for k in keys):
                        resume_score += mark
                        st.success(f"{keys[0].title()} section found (+{mark})")
                    else:
                        st.warning(f"Consider adding {keys[0].title()} section")

                if resume_score > 100:
                    resume_score = 100

                st.subheader("**Resume Score📝**")
                my_bar = st.progress(0)

                score = 0
                for i in range(resume_score):
                    score += 1
                    time.sleep(0.01)
                    my_bar.progress(i + 1)
                st.success('** Your Resume Writing Score: ' + str(resume_score) + '**')
                st.warning(
                    "** Note: This score is calculated based on the content that you have added in your Resume. **"
                )
                st.balloons()

                insert_data(resume_data['name'], resume_data.get('email', 'noemail@example.com'), str(resume_score), timestamp,
                            str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']),
                            str(recommended_skills), str(rec_course))






                save_to_csv(
                    resume_data['name'],
                    resume_data['email'],
                    resume_data['skills'],
                    resume_data['no_of_pages'],
                    cand_level,
                    reco_field
                )
                ## Resume writing video
                st.header("**Bonus Video for Resume Writing Tips💡**")
                resume_vid = random.choice(resume_videos)
                res_vid_title = fetch_yt_video(resume_vid)
                st.subheader("✅ **" + res_vid_title + "**")
                st.video(resume_vid)

                ## Interview Preparation Video
                st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
                interview_vid = random.choice(interview_videos)
                int_vid_title = fetch_yt_video(interview_vid)
                st.subheader("✅ **" + int_vid_title + "**")
                st.video(interview_vid)

                connection.commit()
            else:
                st.error('Something went wrong..')
    else:
        ## Admin Side
        st.success('Welcome to Admin Side')
        # st.sidebar.subheader('**ID / Password Required!**')

        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')
        if st.button('Login'):
            if ad_user == 'admin' and ad_password == 'Tomas@5780':
                st.success("Admin Login Successful")
                # ===== Academic Dataset Section =====
                st.subheader("📁 Academic Resume Dataset (CSV)")
                dataset_df = load_academic_dataset()

                if not dataset_df.empty:
                    st.dataframe(dataset_df)
                else:
                    st.warning("Dataset file not found!")
                # ===================================

                # Display Data
                cursor.execute('''SELECT*FROM user_data''')
                data = cursor.fetchall()
                st.header("**User's👨‍💻 Data**")
                df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page',
                                                 'Predicted Field', 'User Level', 'Actual Skills', 'Recommended Skills',
                                                 'Recommended Course'])
                st.dataframe(df)
                st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
                st.subheader("📈 Predicted Field Distribution")
                fig = px.pie(df, names="Predicted Field")
                st.plotly_chart(fig)

                st.subheader("📈 Experience Level Distribution")
                fig2 = px.pie(df, names="User Level")
                st.plotly_chart(fig2)
                ## Admin Side Data
                query = 'select * from user_data;'
                plot_data = pd.read_sql(query, connection)

                ## Pie chart for predicted field recommendations
                labels = plot_data.Predicted_Field.unique()
                print(labels)
                values = plot_data.Predicted_Field.value_counts()
                print(values)
                st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
                fig = px.pie(df, values=values, names=labels, title='Predicted Field according to the Skills')
                st.plotly_chart(fig)

                ### Pie chart for User's👨‍💻 Experienced Level
                labels = plot_data.User_level.unique()
                values = plot_data.User_level.value_counts()
                st.subheader("📈 ** Pie-Chart for User's👨‍💻 Experienced Level**")
                fig = px.pie(df, values=values, names=labels, title="Pie-Chart📈 for User's👨‍💻 Experienced Level")
                st.plotly_chart(fig)


            else:
                st.error("Wrong ID & Password Provided")


run()