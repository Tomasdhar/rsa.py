import os
import csv
import streamlit as st
import nltk
import re
import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

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
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import yt_dlp
import plotly.express as px
# SQLite connection
import sqlite3

st.set_page_config(
    page_title="ResumeIQ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

hide_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""

st.markdown(hide_menu, unsafe_allow_html=True)

st.title("ResumeIQ: Smart Resume Analyser")
st.write("Analyze smarter. Get hired faster 🔥")

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
def section_found(text, keywords):
    text = text.lower()
    return any(k.lower() in text for k in keywords)

def clean_text(text):
    return re.findall(r'\w+', text.lower())


def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()

    laparams = LAParams(
        line_margin=0.2,
        word_margin=0.1,
        char_margin=2.0,
        all_texts=True
    )

    converter = TextConverter(resource_manager, fake_file_handle, laparams=laparams)
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)

    text = fake_file_handle.getvalue()

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
    page_title="ResumeIQ",
    page_icon='./Logo/SRA_Logo.ico',
    layout="wide"
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

# =========================
# Helper Functions (TOP AREA)
# =========================

def get_resume_advice(resume_text, resume_score):
    advice = []

    text = resume_text.lower()

    if not re.search(r'\b(objective|summary|profile)\b', text):
        advice.append("🟡 Add a strong career summary (2–3 lines).")

    if not re.search(r'\b(education|university|college|b\.?tech|bsc|msc|degree)\b', text):
        advice.append("🟡 Include education details.")

    if not re.search(r'\b(experience|intern|worked|employment|job)\b', text):
        advice.append("🟡 Add work experience.")

    if not re.search(r'\b(python|java|sql|react|django|flask|ml|ai)\b', text):
        advice.append("🟡 Add technical skills.")

    if not re.search(r'\b(project|built|developed|created)\b', text):
        advice.append("🟡 Add projects.")

    if resume_score < 60:
        advice.append("🔴 Improve resume structure and ATS keywords.")
    elif resume_score < 80:
        advice.append("🟠 Good resume, but add achievements.")
    else:
        advice.append("🟢 Strong resume!")

    return advice

def calculate_ats_score(resume_text, job_desc):
    if not job_desc:
        return 0

    resume_words = set(clean_text(resume_text))
    job_words = set(clean_text(job_desc))

    common = resume_words.intersection(job_words)

    if len(job_words) == 0:
        return 0

    return round((len(common) / len(job_words)) * 100, 2)

    resume_words = set(resume_text.lower().split())
    job_words = set(job_desc.lower().split())

    common_words = resume_words.intersection(job_words)

    if len(job_words) == 0:
        return 0

    score = (len(common_words) / len(job_words)) * 100
    return round(score, 2)

def skill_gap_analyzer(resume_text, job_desc):
    resume_skills = set(re.findall(r'\b(python|java|sql|react|django|flask|ml|ai|aws|docker)\b', resume_text.lower()))
    job_skills = set(re.findall(r'\b(python|java|sql|react|django|flask|ml|ai|aws|docker)\b', job_desc.lower()))

    return list(job_skills - resume_skills)

def resume_rewrite_suggestions(resume_text):
    suggestions = []

    if len(resume_text.split()) < 150:
        suggestions.append("Expand your resume with more project and experience details.")

    if "project" not in resume_text.lower():
        suggestions.append("Add 2–3 real projects with technologies used.")

    if "achievement" not in resume_text.lower():
        suggestions.append("Add measurable achievements (impact, numbers, results).")

    suggestions.append("Use action verbs: Developed, Built, Designed, Optimized.")

    return suggestions

def detect_industry(resume_text):
    text = resume_text.lower()

    if any(word in text for word in ["tensorflow", "pytorch", "machine learning", "data"]):
        return "Data Science"
    elif any(word in text for word in ["react", "html", "css", "javascript"]):
        return "Web Development"
    elif any(word in text for word in ["android", "kotlin", "flutter"]):
        return "Android Development"
    else:
        return "General IT"

def run():

    st.subheader("📌 Job Description Input (for ATS Analysis)")
    job_desc = st.text_area("Paste Job Description here")
    reco_field = ""
    cand_level = ""
    rec_course = []
    recommended_skills = []

    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    # link = '[©Developed by Spidy20](http://github.com/spidy20)'
    # st.sidebar.markdown(link, unsafe_allow_html=True)
    from PIL import Image
    import os

    BASE_DIR = os.path.dirname(__file__)
    logo_path = os.path.join(BASE_DIR, "Logo", "SRA_Logo.jpg")

    try:
        img = Image.open(logo_path)
        st.image(img, width=250)
    except Exception as e:
        st.error(f"Logo not found. Path: {logo_path}")
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
            ts = time.time()
            cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            timestamp = str(cur_date + '_' + cur_time)
            st.success("Resume uploaded successfully")
            os.makedirs("Uploaded_Resumes", exist_ok=True)

            save_image_path = os.path.join("Uploaded_Resumes", pdf_file.name)

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
            name_match = re.findall(r"[a-zA-Z ]{3,30}", resume_text)
            name = name_match[0].title() if name_match else "Not Found"

            # ✅ Skills (basic extraction)

            # Page count (simple OR use function)
            no_of_pages = 1

            resume_data = {
                    "name": name,
                    "email": email,
                    "mobile_number": phone,
                    "no_of_pages": no_of_pages,

            }

            resume_data["skills"] = list(set(re.findall(
                r'\b(python|java|sql|react|django|flask|machine learning|ai|html|css|javascript)\b',
                resume_text.lower()
            )))

            sections = {
                ('objective', 'career objective', 'summary', 'profile'): 10,
                ('education', 'academic', 'university', 'college', 'degree', 'b.e', 'btech'): 15,
                ('experience', 'work experience', 'employment', 'internship'): 20,
                ('skills', 'technical skills', 'core skills'): 20,
                ('projects', 'project', 'developed', 'built'): 15,
                ('certification', 'certifications', 'courses'): 10,
                ('achievement', 'achievements', 'awards'): 10
            }

            st.header("**Resume Analysis**")


            st.subheader("**Your Basic info**")
            st.text('Name: ' + resume_data['name'])
            st.text('Email: ' + resume_data['email'])
            st.text('Contact: ' + resume_data['mobile_number'])
            st.text('Resume pages: ' + str(resume_data['no_of_pages']))
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

            if resume_data['skills']:
                    st.write("### 🛠 Detected Skills:")

                    for skill in resume_data['skills']:
                        st.success(skill)

            else:
                st.warning("No skills detected in your resume")
                    ##  recommendation
                ds_keyword = [
                        'tensorflow', 'keras', 'pytorch',
                        'machine learning', 'deep learning', 'flask'
                ]

                web_keyword = [
                    'react', 'django', 'javascript'
                ]
                android_keyword = ['android', 'kotlin']
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



                ### Resume writing recommendation

                from pdfminer.pdfpage import PDFPage

                def get_pdf_page_count(file_path):
                    with open(file_path, "rb") as f:
                        return len(list(PDFPage.get_pages(f)))

                resume_data["no_of_pages"] = get_pdf_page_count(save_image_path)

                sections = {
                    ('objective', 'career objective', 'summary', 'profile'): 10,
                    ('education', 'academic', 'university', 'college', 'degree', 'b.e', 'btech'): 15,
                    ('experience', 'work experience', 'employment', 'internship'): 20,
                    ('skills', 'technical skills', 'core skills'): 20,
                    ('projects', 'project', 'developed', 'built'): 15,
                    ('certification', 'certifications', 'courses'): 10,
                    ('achievement', 'achievements', 'awards'): 10
                }
            st.subheader("**Resume Tips & Ideas💡**")

            resume_score = 0

            for keys, mark in sections.items():
                if section_found(resume_text, keys):
                    resume_score += mark
                    st.success(f"{keys[0].title()} section found (+{mark})")
                else:
                    st.warning(f"Consider adding {keys[0].title()} section")

            resume_score = min(resume_score, 100)


            # PROFESSIONAL ADVICE BLOCK

            st.subheader("📌 Professional Resume Improvement Advice")

            advice_list = get_resume_advice(resume_text, resume_score)

            for tip in advice_list:
                st.write(tip)

            st.subheader("**Resume Score📝**")
            my_bar = st.progress(0)

            st.subheader("📊 ATS Match Score")

            ats_score = calculate_ats_score(resume_text, job_desc)

            st.metric("ATS Score", f"{ats_score} %")

            st.subheader("🧠 Skill Gap Analysis")

            missing_skills = skill_gap_analyzer(resume_text, job_desc)

            if missing_skills:
                for s in missing_skills:
                    st.write("🔴", s)
            else:
                st.success("No major skill gaps found!")

            st.subheader("🧭 Industry Detection")

            industry = detect_industry(resume_text)
            st.info(f"Detected Field: {industry}")

            st.subheader("✍️ Resume Rewrite Suggestions")

            for tip in resume_rewrite_suggestions(resume_text):
                st.write("✔", tip)

            st.subheader("🏆 Hireability Score")

            final_score = (
                    resume_score * 0.4 +
                    ats_score * 0.4 +
                    max(0, 20 - len(missing_skills) * 2)
            )

            st.success(f"Your Hireability Score: {round(final_score, 2)} / 100")



            score = 0
            for i in range(resume_score):
                time.sleep(0.01)
                my_bar.progress(i + 1)
            st.success('** Your Resume Writing Score: ' + str(resume_score) + '**')
            st.warning(
                    "** Note: This score is calculated based on the content that you have added in your Resume. **"
            )
            st.balloons()

            insert_data(resume_data['name'], resume_data.get('email', 'noemail@example.com'), str(resume_score),
                            timestamp,
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
            res_vid_title = "Resume Writing Tips Video"
            st.subheader("✅ " + res_vid_title)
            st.video(resume_vid)
            ## Interview Preparation Video
            st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
            interview_vid = random.choice(interview_videos)
            int_vid_title = "Interview Preparation Video"
            st.subheader("✅ " + int_vid_title)
            st.video(interview_vid)

            connection.commit()


    ## Admin Side
    elif choice == "Admin":
        st.success("Welcome to Admin Dashboard")

        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type="password")

        if st.button("Login"):

            if ad_user == "admin" and ad_password == "Tomas@5780":
                st.success("Admin Login Successful")

                df = load_academic_dataset()

                # 📊 1. USER ANALYTICS
                st.subheader("📊 Resume Analysis Stats")

                if not df.empty:
                    st.write("Total Users:", len(df))

                    if "job_field" in df.columns:
                        st.bar_chart(df["job_field"].value_counts())

                # 📈 2. EXPERIENCE LEVEL
                st.subheader("📈 Experience Distribution")

                if "experience_level" in df.columns:
                    st.bar_chart(df["experience_level"].value_counts())

                # 📂 3. SKILL INSIGHT
                st.subheader("🧠 Skills Overview")

                if "skills" in df.columns:
                    all_skills = df["skills"].dropna().str.cat(sep="|").split("|")
                    skill_series = pd.Series(all_skills).value_counts().head(10)
                    st.bar_chart(skill_series)

                # 📥 4. DOWNLOAD
                st.subheader("📥 Download Full Report")
                st.markdown(
                    get_table_download_link(df, "resume_report.csv", "Download CSV Report"),
                    unsafe_allow_html=True
                )

                # 🔍 5. SEARCH
                st.subheader("🔍 Search Candidate")
                search = st.text_input("Enter Name or Email")

                if search:
                    result = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
                    st.dataframe(result)

                # 🏆 6. TOP CANDIDATES
                st.subheader("🏆 Top Candidates")

                if "resume_score" in df.columns:
                    df["resume_score"] = pd.to_numeric(df["resume_score"], errors="coerce")
                    st.dataframe(df.sort_values("resume_score", ascending=False).head(10))

            else:
                st.error("Wrong ID & Password")




run()




