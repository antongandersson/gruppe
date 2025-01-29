import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import plotly.express as px
from streamlit.components.v1 import html

class Student:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.preferred_partners: List[int] = []
        self.preferred_topic: Optional[str] = None
        self.secondary_topic: Optional[str] = None
    
    def __str__(self):
        return f"{self.name} (ID: {self.id})"

class Group:
    def __init__(self, members: List[Student], topic: str, score: float):
        self.members = members
        self.topic = topic
        self.score = score
    
    def __str__(self):
        return f"Emne: {self.topic}, Score: {self.score:.2f}, Medlemmer: {', '.join(str(member) for member in self.members)}"

class GroupFormationSystem:
    def __init__(self, num_students: int, topics: List[str], student_names: List[str]):
        self.topics = topics
        self.students = [Student(i+1, student_names[i]) for i in range(num_students)]
        self.max_group_size = 4
    
    def calculate_pair_score(self, student1: Student, student2: Student) -> float:
        score = 0.0
        
        if student2.id in student1.preferred_partners[:1] and student1.id in student2.preferred_partners[:1]:
            score += 10.0
        elif student2.id in student1.preferred_partners and student1.id in student2.preferred_partners:
            score += 5.0
        elif student2.id in student1.preferred_partners or student1.id in student2.preferred_partners:
            score += 2.0
        
        if student1.preferred_topic == student2.preferred_topic:
            score += 5.0
        elif (student1.preferred_topic == student2.secondary_topic or 
              student1.secondary_topic == student2.preferred_topic):
            score += 2.0
        
        return score
    
    def create_score_matrix(self) -> np.ndarray:
        n_students = len(self.students)
        matrix = np.zeros((n_students, n_students))
        
        for i in range(n_students):
            for j in range(i+1, n_students):
                score = self.calculate_pair_score(self.students[i], self.students[j])
                matrix[i][j] = score
                matrix[j][i] = score
        
        return matrix
    
    def find_best_groups(self, score_matrix: np.ndarray) -> List[Group]:
        unassigned = set(range(len(self.students)))
        groups = []

        while unassigned:
            best_group = None
            best_score = -1
            best_topic = None

            for size in range(2, min(self.max_group_size + 1, len(unassigned) + 1)):
                for members in self._get_possible_groups(list(unassigned), size):
                    if not members:
                        continue
                    
                    score = self._calculate_group_score(members, score_matrix)
                    topic_counts = {}
                    
                    for i in members:
                        topic = self.students[i].preferred_topic
                        if topic:
                            topic_counts[topic] = topic_counts.get(topic, 0) + 1
                    
                    if not topic_counts:
                        continue
                    
                    current_topic = max(topic_counts.items(), key=lambda x: x[1])[0]
                    
                    if score > best_score:
                        best_score = score
                        best_group = members
                        best_topic = current_topic

            if best_group and best_topic:
                group_members = [self.students[i] for i in best_group]
                groups.append(Group(group_members, best_topic, best_score))
                unassigned -= set(best_group)
            else:
                remaining_students = [self.students[i] for i in unassigned]
                
                while remaining_students:
                    current_group = remaining_students[:self.max_group_size]
                    remaining_students = remaining_students[self.max_group_size:]
                    
                    topic_preferences = {}
                    for student in current_group:
                        if student.preferred_topic:
                            topic_preferences[student.preferred_topic] = topic_preferences.get(student.preferred_topic, 0) + 1
                    
                    chosen_topic = max(topic_preferences.items(), key=lambda x: x[1])[0] if topic_preferences else self.topics[0]
                    groups.append(Group(current_group, chosen_topic, 0.0))
                
                break

        return groups

    def _get_possible_groups(self, students: List[int], size: int) -> List[List[int]]:
        if size == 1:
            return [[s] for s in students]
        
        groups = []
        for i in range(len(students)):
            current = students[i]
            others = students[i+1:]
            for subgroup in self._get_possible_groups(others, size-1):
                groups.append([current] + subgroup)
        return groups
    
    def _calculate_group_score(self, members: List[int], score_matrix: np.ndarray) -> float:
        score = 0.0
        for i in range(len(members)):
            for j in range(i+1, len(members)):
                score += score_matrix[members[i]][members[j]]
        return score
    
    def set_preferences(self, student_id: int, partner_ids: List[int], primary_topic: str, secondary_topic: str = None):
        student = next(s for s in self.students if s.id == student_id)
        student.preferred_partners = partner_ids
        student.preferred_topic = primary_topic
        student.secondary_topic = secondary_topic

    def reset_preferences(self):
        student_names = [student.name for student in self.students]
        self.students = [Student(i+1, name) for i, name in enumerate(student_names)]

def initialize_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = 'setup'
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False
    if 'system' not in st.session_state:
        st.session_state.system = None
    if 'preferences_set' not in st.session_state:
        st.session_state.preferences_set = set()
    if 'num_students' not in st.session_state:
        st.session_state.num_students = 35
    if 'topics' not in st.session_state:
        st.session_state.topics = [
            "Matematik", "Dansk", "Historie", "Biologi",
            "Fysik", "Kemi", "Engelsk", "Samfundsfag", "Geografi"
        ]
    if 'student_names' not in st.session_state:
        st.session_state.student_names = [f"Elev {i+1}" for i in range(35)]
    if 'first_visit' not in st.session_state:
        st.session_state.first_visit = True


def go_to_setup():
    st.session_state.page = 'setup'
    st.session_state.setup_complete = False

def go_to_main():
    st.session_state.page = 'main'
    st.session_state.setup_complete = True


def show_stepper(current_step):
    steps = ["Konfiguration", "Elevvalg", "Gruppedannelse"]
    html = f"""
    <div class="stepper-container">
        {''.join([
            f'<div class="stepper-item {"active" if i == current_step else ""}">'
            f'<span style="background: white; padding: 0 1rem;">{step}</span>'
            '</div>' 
            for i, step in enumerate(steps)
        ])}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def show_animated_success(message):
    st.markdown(f"""
    <div class="custom-card" style="animation: fadeIn 0.5s ease-in;">
        ✅ {message}
    </div>
    <style>
    @keyframes fadeIn {{
        0% {{ opacity: 0; transform: translateY(-10px); }}
        100% {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    """, unsafe_allow_html=True)

def display_student_status(system: GroupFormationSystem, preferences_set: set):
    st.subheader("Elevstatus")
    search_query = st.text_input("Søg efter elever", key="student_search")
    
    has_preferences = [s for s in system.students if s.id in preferences_set]
    missing_preferences = [s for s in system.students if s.id not in preferences_set]
    
    if search_query:
        has_preferences = [s for s in has_preferences if search_query.lower() in s.name.lower()]
        missing_preferences = [s for s in missing_preferences if search_query.lower() in s.name.lower()]
    
    tab1, tab2 = st.tabs(["Har valgt", "Mangler valg"])
    
    with tab1:
        cols = st.columns(5)
        for i, student in enumerate(has_preferences):
            with cols[i % 5]:
                st.markdown(f"""
                <div class="custom-card">
                    ✅ {student.name}<br>
                    <small>Score: {sum(system.calculate_pair_score(student, s) for s in has_preferences if s != student):.1f}</small>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        cols = st.columns(5)
        for i, student in enumerate(missing_preferences):
            with cols[i % 5]:
                st.markdown(f"""
                <div class="custom-card">
                    ⭕ {student.name}<br>
                    <small>Ikke indsendt</small>
                </div>
                """, unsafe_allow_html=True)

def setup_page():
    if st.session_state.first_visit:
        with st.expander("Velkommen til GruppeDanner Pro!", expanded=True):
            st.write("""
            **Første gangs guide:**
            1. Konfigurer antal elever og emner
            2. Tilpas elevnavne og emnenavne
            3. Klik 'Start konfiguration' når du er klar
            """)
            if st.button("Start nu"):
                st.session_state.first_visit = False
                st.rerun()
        return

    st.title("Gruppedannelsessystem - Konfiguration")
    
    with st.expander("❓ Hjælp til konfiguration", expanded=False):
        st.write("""
        - **Antal elever**: Vælg det samlede antal deltagere
        - **Emner**: Definer minimum 2 fagområder
        - **Elevnavne**: Skriv rigtige navne eller brug standard
        """)

    col1, col2 = st.columns(2)
    
    with col1:
        num_students = st.number_input(
            "Antal elever", 
            min_value=2, 
            max_value=100, 
            value=st.session_state.num_students,
            key="num_students_input"
        )
        
    with col2:
        num_topics = st.number_input(
            "Antal emner", 
            min_value=1, 
            max_value=20, 
            value=len(st.session_state.topics),
            key="num_topics_input"
        )

    if st.session_state.num_students != len(st.session_state.student_names):
        if st.session_state.num_students > len(st.session_state.student_names):
            for i in range(len(st.session_state.student_names), st.session_state.num_students):
                st.session_state.student_names.append(f"Elev {i+1}")
        else:
            st.session_state.student_names = st.session_state.student_names[:st.session_state.num_students]

    if num_topics != len(st.session_state.topics):
        if num_topics > len(st.session_state.topics):
            for i in range(len(st.session_state.topics), num_topics):
                st.session_state.topics.append(f"Emne {i+1}")
        else:
            st.session_state.topics = st.session_state.topics[:num_topics]

    st.subheader("Emner")
    topics_col1, topics_col2 = st.columns(2)
    with topics_col1:
        for i in range((len(st.session_state.topics) + 1) // 2):
            topic = st.text_input(
                f"Emne {i+1}", 
                value=st.session_state.topics[i],
                key=f"topic_{i}"
            )
    with topics_col2:
        for i in range((len(st.session_state.topics) + 1) // 2, len(st.session_state.topics)):
            topic = st.text_input(
                f"Emne {i+1}", 
                value=st.session_state.topics[i],
                key=f"topic_{i}"
            )

    st.subheader("Elevnavne")
    students_col1, students_col2 = st.columns(2)
    with students_col1:
        for i in range((len(st.session_state.student_names) + 1) // 2):
            name = st.text_input(
                f"Elev {i+1}", 
                value=st.session_state.student_names[i],
                key=f"student_{i}"
            )
    with students_col2:
        for i in range((len(st.session_state.student_names) + 1) // 2, len(st.session_state.student_names)):
            name = st.text_input(
                f"Elev {i+1}", 
                value=st.session_state.student_names[i],
                key=f"student_{i}"
            )

    if st.button("Start konfiguration ⏎", key="start_btn") or st.session_state.get("enter_pressed"):
        st.session_state.system = GroupFormationSystem(
            st.session_state.num_students,
            st.session_state.topics,
            st.session_state.student_names
        )
        st.session_state.preferences_set = set()
        go_to_main()
        st.rerun()

    st.components.v1.html(
        """
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                window.parent.document.querySelector('button[key="start_btn"]').click();
            }
        });
        </script>
        """
    )

def main_page():
    st.title("Gruppedannelsessystem")
    show_stepper(1)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("⬅️ Tilbage til konfiguration", use_container_width=True):
            go_to_setup()
            st.rerun()
    with col2:
        if st.button("🔄 Nulstil præferencer", use_container_width=True):
            st.session_state.system.reset_preferences()
            st.session_state.preferences_set = set()
            st.success("Præferencer nulstillet!")
            st.rerun()
    
    display_student_status(st.session_state.system, st.session_state.preferences_set)
    st.markdown("---")
    
    with st.sidebar:
        st.header("Indstillinger")
        high_contrast = st.toggle("Høj kontrast tilstand")
        if high_contrast:
            st.markdown('<style>[data-high-contrast="true"] { filter: contrast(1.4); }</style>', unsafe_allow_html=True)
        
        st.markdown("---")
        selected_student_id = st.selectbox(
            "Vælg elev",
            options=[s.id for s in st.session_state.system.students],
            format_func=lambda x: st.session_state.system.students[x-1].name
        )
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Partnerpræferencer")
        partner_options = [s.id for s in st.session_state.system.students if s.id != selected_student_id]
        selected_partners = st.multiselect(
            "Prioriterede partnere (træk for at ændre rækkefølge)",
            options=partner_options,
            format_func=lambda x: st.session_state.system.students[x-1].name
        )
    with col2:
        st.subheader("Emnevalg")
        primary_topic = st.selectbox(
            "Primært emne",
            options=st.session_state.system.topics
        )
        secondary_topic = st.selectbox(
            "Sekundært emne",
            options=["Ingen"] + st.session_state.system.topics
        )
    
    if st.button("Gem valg"):
        st.session_state.system.set_preferences(
            selected_student_id,
            selected_partners,
            primary_topic,
            None if secondary_topic == "Ingen" else secondary_topic
        )
        st.session_state.preferences_set.add(selected_student_id)
        show_animated_success(f"Valg gemt for {st.session_state.system.students[selected_student_id-1].name}")
        st.rerun()
    
    st.subheader("Samlet status")
    progress = len(st.session_state.preferences_set) / len(st.session_state.system.students)
    st.progress(progress)
    st.write(f"{len(st.session_state.preferences_set)}/{len(st.session_state.system.students)} elever har indsendt valg")
    
    if st.button("🔄 Dan grupper"):
        with st.spinner("Danner grupper..."):
            score_matrix = st.session_state.system.create_score_matrix()
            groups = st.session_state.system.find_best_groups(score_matrix)
            st.session_state.groups = groups
            
            st.subheader("Resultater")
            for i, group in enumerate(groups, 1):
                with st.expander(f"Gruppe {i}: {group.topic} (Score: {group.score:.1f})", expanded=i==1):
                    st.write(f"**Antal medlemmer:** {len(group.members)}")
                    st.write("**Elever:**")
                    for member in group.members:
                        st.write(f"- {member.name}")
            
            st.subheader("Live Dashboard")
            cols = st.columns([2, 1])
            with cols[0]:
                if groups:
                    topics = [group.topic for group in groups]
                    fig = px.pie(
                        values=[topics.count(t) for t in set(topics)],
                        names=list(set(topics)),
                        title="Emnefordeling"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            with cols[1]:
                with st.expander("📊 Statusoversigt", expanded=True):
                    st.metric("Grupper dannet", len(groups))
                    st.metric("Gns. score", f"{np.mean([g.score for g in groups]):.1f}")
                    st.progress(progress)
            
            if len([m for g in groups for m in g.members]) < len(st.session_state.system.students):
                st.warning(f"{len(st.session_state.system.students) - len([m for g in groups for m in g.members])} elever kunne ikke placeres")

def main():
    st.set_page_config(
        page_title="GruppeDanner Pro",
        page_icon="👥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
        .stButton>button {
            transition: all 0.3s ease;
            border-radius: 8px !important;
        }
        .stButton>button:hover {
            transform: scale(1.05);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .stExpander {
            background: #f8f9fa;
            border-radius: 10px !important;
            border: 1px solid #e9ecef !important;
        }
        .stProgress > div > div > div {
            background-color: #2563eb !important;
        }
        .metric-box {
            padding: 1.5rem;
            background: #ffffff;
            border-radius: 10px;
            border: 1px solid #e9ecef;
            margin: 0.5rem 0;
        }
        .github-corner {
            position: absolute;
            top: 0;
            right: 0;
            z-index: 9999;
        }
        .custom-card {
            padding: 1.5rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .stepper-container {
            display: flex;
            justify-content: space-between;
            margin: 2rem 0;
        }
        .stepper-item {
            flex: 1;
            text-align: center;
            padding: 1rem;
            position: relative;
        }
        .stepper-item.active {
            color: #2563eb;
            font-weight: 600;
        }
        .stepper-item::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 2px;
            background: #e9ecef;
            top: 50%;
            left: 50%;
            transform: translateY(-50%);
            z-index: -1;
        }
        @media (max-width: 768px) {
            .stColumn {
                flex-direction: column !important;
            }
        }
        [data-high-contrast="true"] {
            filter: contrast(1.4);
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="github-corner">
        <a href="https://github.com/antongandersson" target="_blank">
            <svg width="80" height="80" viewBox="0 0 250 250" style="fill:#2563eb; color:#fff; position: absolute; top: 0; border: 0; right: 0;">
                <path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path>
                <path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path>
                <path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.9 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path>
            </svg>
        </a>
    </div>
    """, unsafe_allow_html=True)

    initialize_session_state()
    
    if st.session_state.page == 'setup':
        setup_page()
    else:
        main_page()

if __name__ == "__main__":
    main()