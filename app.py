import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import plotly.express as px
import plotly.graph_objects as go
from streamlit.components.v1 import html
from fuzzywuzzy import process
import Levenshtein
import networkx as nx

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
        
        # Vægtet scoring for partnerprioriteringer
        priority_weights = {0: 4.0, 1: 2.5, 2: 1.5}  # Eksempel: Første valg=4, andet=2.5, tredje=1.5
        
        # Tjek gensidighed og prioritetsniveau
        s1_priority = None
        s2_priority = None
        
        if student2.id in student1.preferred_partners:
            s1_priority = student1.preferred_partners.index(student2.id)
            if s1_priority < 3:  # Kun de første 3 prioriteringer tæller
                score += priority_weights.get(s1_priority, 0)
        
        if student1.id in student2.preferred_partners:
            s2_priority = student2.preferred_partners.index(student1.id)
            if s2_priority < 3:
                score += priority_weights.get(s2_priority, 0)
        
        # Gensidighedsbonus baseret på prioritetsforskelle
        if s1_priority is not None and s2_priority is not None:
            priority_diff = abs(s1_priority - s2_priority)
            score += max(3.0 - priority_diff, 0)  # Bonus: 3 for perfekt match, 0 ved stor forskel
        
        # Eksisterende emnelogik
        if student1.preferred_topic == student2.preferred_topic:
            score += 3.0
        elif (student1.preferred_topic == student2.secondary_topic or 
            student1.secondary_topic == student2.preferred_topic):
            score += 1.5
        
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
    if 'guided_tour_step' not in st.session_state:
        st.session_state.guided_tour_step = 0

def go_to_setup():
    st.session_state.page = 'setup'
    st.session_state.setup_complete = False

def go_to_main():
    st.session_state.page = 'main'
    st.session_state.setup_complete = True

def show_stepper(current_step):
    steps = [
        {"icon": "📝", "title": "Konfiguration", "tooltip": "Indstil grundlæggende parametre"},
        {"icon": "👤", "title": "Elevvalg", "tooltip": "Indsaml elevpræferencer"},
        {"icon": "👥", "title": "Gruppedannelse", "tooltip": "Se og rediger grupper"}
    ]
    
    stepper_html = f"""
    <div class="stepper-container" style="position: relative; margin: 2rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            {''.join([
                f'<div style="flex: 1; text-align: center; position: relative; margin: 0 1.5rem;" data-tooltip="{step["tooltip"]}">'
                f'  <div class="phase-icon" style="color: {"#3b82f6" if i == current_step else "#cccccc"};'
                f'       border: 2px solid {"#3b82f6" if i == current_step else "#eeeeee"};'
                f'       border-radius: 50%; width: 40px; height: 40px; display: inline-flex;'
                f'       align-items: center; justify-content: center;">{step["icon"]}</div>'
                f'  <div style="margin-top: 0.5rem; font-weight: {"bold" if i == current_step else "normal"}">{step["title"]}</div>'
                f'</div>'
                for i, step in enumerate(steps)
            ])}
        </div>
    </div>
    """
    st.markdown(stepper_html, unsafe_allow_html=True)

    html("""
    <script>
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.addEventListener('mouseover', () => {
            const tooltip = document.createElement('div');
            tooltip.style.position = 'absolute';
            tooltip.style.background = 'rgba(0,0,0,0.8)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.top = '-40px';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translateX(-50%)';
            tooltip.style.whiteSpace = 'nowrap';
            tooltip.textContent = el.dataset.tooltip;
            el.appendChild(tooltip);
        });
        el.addEventListener('mouseout', () => {
            el.removeChild(el.lastChild);
        });
    });
    </script>
    """)

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
    
    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input("Søg efter elever", key="student_search")
    with col2:
        filter_status = st.selectbox("Filtrer efter status", ["Alle", "Udfyldt", "Mangler"], index=1)
    
    all_names = [s.name for s in system.students]
    if search_query:
        matches = process.extract(search_query, all_names, limit=5)
        filtered_students = [s for s in system.students if s.name in [m[0] for m in matches]]
    else:
        filtered_students = system.students
    
    if filter_status == "Udfyldt":
        filtered_students = [s for s in filtered_students if s.id in preferences_set]
    elif filter_status == "Mangler":
        filtered_students = [s for s in filtered_students if s.id not in preferences_set]
    
    for student in filtered_students:
        completeness = "full" if student.id in preferences_set else "partial"
        with st.container():
            st.markdown(f"""
            <div class="student-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4>{student.name}</h4>
                        <div style="font-size: 0.9em;">
                            <div>📌 Primært emne: {student.preferred_topic or 'Ikke valgt'}</div>
                            <div>📌 Sekundært emne: {student.secondary_topic or 'Ikke valgt'}</div>
                            <div>🤝 Valgte partnere: {len(student.preferred_partners)}</div>
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.2em; font-weight: bold; 
                            color: {'#4caf50' if completeness == 'full' else '#ffd600'}">
                            {len(student.preferred_partners)*10}%
                        </div>
                        <small>Komplethed</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def show_network_graph(system):
    st.subheader("Elevnetværk")
    G = nx.Graph()
    
    for student in system.students:
        G.add_node(student.id, label=student.name, topic=student.preferred_topic)
        for partner in student.preferred_partners:
            if partner in [s.id for s in system.students]:
                partner_student = next(s for s in system.students if s.id == partner)
                score = system.calculate_pair_score(student, partner_student)
                G.add_edge(student.id, partner, weight=score)
    
    pos = nx.spring_layout(G, seed=42)
    
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines')
    
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(G.nodes[node]['label'])
        node_color.append(hash(G.nodes[node]['topic']) % 0xFFFFFF if G.nodes[node]['topic'] else 0xCCCCCC)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=True,
            colorscale='Viridis',
            size=20,
            color=node_color,
            line_width=2))
    
    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    
    st.plotly_chart(fig, use_container_width=True)

def add_keyboard_shortcuts():
    html("""
    <script>
    document.addEventListener('keydown', function(e) {
        if(e.altKey && e.key === 's') {
            window.parent.document.querySelector('button:has-text("Gem valg")').click();
        }
        if(e.altKey && e.key === 'n') {
            window.parent.document.querySelector('button:has-text("Næste")').click();
        }
    });
    </script>
    """)

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
            # Opdater session state med den nye værdi
            st.session_state.num_students = num_students
            
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
    # Centrer titel
    st.markdown("""
    <style>
        .centered-title {
            text-align: center;
            font-size: 2.5em !important;
            margin-bottom: 1.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<h1 class="centered-title">Gruppedannelsessystem</h1>', unsafe_allow_html=True)
    
    show_stepper(1)

    # Tilføj custom CSS
    st.markdown("""
    <style>
        /* Primærknapper */
        div[data-testid="stButton"] > button:not([kind="secondary"]) {
            width: 100% !important;
            padding: 1rem !important;
            border-radius: 10px !important;
            transition: all 0.3s ease !important;
        }

        /* Tilbage-knap */
        div[data-testid="stButton"] > button:first-child {
            background: #3b82f6 !important;
            color: white !important;
        }

        /* Nulstil-knap */
        div[data-testid="stButton"] > button:nth-child(2) {
            background: #ef4444 !important;
            color: white !important;
        }

        /* Hover effekter til primærknapper */
        div[data-testid="stButton"] > button:not([kind="secondary"]):hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }

        /* Mindre sekundærknapper */
        div[data-testid="stButton"] > button[kind="secondary"] {
            padding: 0.5rem 1rem !important;
            font-size: 0.9em !important;
            border-radius: 8px !important;
            width: auto !important;
            min-height: unset !important;
            transition: all 0.2s ease !important;
            background: #f0f2f6 !important;
            color: #333 !important;
            border: 1px solid #ddd !important;
        }

        button[kind="secondary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            background: #e2e6eb !important;
            border-color: #ccc !important;
        }

        /* Dark mode tilpasninger */
        [data-theme="dark"] button[kind="secondary"] {
            background: #2d2d2d !important;
            color: #fff !important;
            border-color: #444 !important;
        }

        [data-theme="dark"] button[kind="secondary"]:hover {
            background: #3d3d3d !important;
            border-color: #555 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Knapper i grid layout
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "⚙️ Tilbage til konfiguration", 
            help="Returner til konfigurationssiden",
            use_container_width=True
        ):
            go_to_setup()
            st.rerun()

    with col2:
        if st.button(
            "♻️ Nulstil præferencer", 
            help="Slet alle indtastede præferencer",
            use_container_width=True
        ):
            st.session_state.system.reset_preferences()
            st.session_state.preferences_set = set()
            st.success("Præferencer nulstillet!")
            st.rerun()

    display_student_status(st.session_state.system, st.session_state.preferences_set)
    st.markdown("---")
    
    with st.sidebar:
        st.header("Indstillinger")
        theme = st.selectbox("Tema", ["Automatisk", "Lyst", "Mørkt"], index=0)
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
            format_func=lambda x: st.session_state.system.students[x-1].name,
            key="partner_select"
        )
    
    with col2:
        st.subheader("Emnevalg")
        primary_topic = st.selectbox(
            "Primært emne",
            options=st.session_state.system.topics,
            key="primary_topic"
        )
        secondary_topic = st.selectbox(
            "Sekundært emne",
            options=["Ingen"] + st.session_state.system.topics,
            key="secondary_topic"
        )
    
    # Gem knap med mindre styling
    if st.button("Gem valg", 
                 key="save_prefs",
                 type="secondary",
                 help="Gemmer den valgte elevs præferencer"):
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
    
    # Gruppedannelsesknap med mindre styling
    if st.button("🔄 Dan grupper", 
                 key="form_groups",
                 type="secondary",
                 help="Start gruppedannelsesprocessen"):
        with st.spinner("Analyserer præferencer..."):
            score_matrix = st.session_state.system.create_score_matrix()
            groups = st.session_state.system.find_best_groups(score_matrix)
            st.session_state.groups = groups
            
            st.subheader("Grupperesultat")
            for i, group in enumerate(groups, 1):
                with st.expander(f"Gruppe {i}: {group.topic} (Score: {group.score:.1f})", expanded=i==1):
                    st.write(f"**Antal medlemmer:** {len(group.members)}")
                    st.write("**Elever:**")
                    for member in group.members:
                        st.write(f"- {member.name}")
            
            st.subheader("Live Dashboard")
            cols = st.columns([2, 1])
            with cols[0]:
                show_network_graph(st.session_state.system)
            with cols[1]:
                with st.expander("📊 Statusoversigt", expanded=True):
                    st.metric("Grupper dannet", len(groups))
                    st.metric("Gennemsnitlig score", f"{sum(g.score for g in groups)/len(groups):.1f}" if groups else "0.0")
                    st.progress(progress)
            
            if len([m for g in groups for m in g.members]) < len(st.session_state.system.students):
                st.warning(f"{len(st.session_state.system.students) - len([m for g in groups for m in g.members])} elever kunne ikke placeres")
    
    # Tema-håndtering
    theme_js = f"""
    <script>
        const setTheme = (isDark) => {{
            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        }};

        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const themeSetting = "{theme}";
        
        if(themeSetting === 'Automatisk') {{
            setTheme(systemDark);
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {{
                setTheme(e.matches);
            }});
        }} else {{
            setTheme(themeSetting === 'Mørkt');
        }}
    </script>
    """
    html(theme_js)

def main():
    st.set_page_config(
        page_title="GruppeDanner Pro",
        page_icon="👥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
        :root {{
            --primary-bg: #ffffff;
            --secondary-bg: #f8f9fa;
            --primary-text: #333333;
            --border-color: #e9ecef;
            --button-bg: #2563eb;
            --button-hover: #1d4ed8;
        }}

        [data-theme="dark"] {{
            --primary-bg: #1a1a1a;
            --secondary-bg: #2d2d2d;
            --primary-text: #ffffff;
            --border-color: #4d4d4d;
            --button-bg: #3b82f6;
            --button-hover: #2563eb;
        }}

        body {{
            background-color: var(--primary-bg) !important;
            color: var(--primary-text) !important;
            transition: all 0.3s ease;
        }}

        .stApp {{
            background-color: var(--primary-bg) !important;
        }}

        .stExpander {{
            background: var(--secondary-bg) !important;
            border-color: var(--border-color) !important;
        }}

        .stButton>button {{
            background-color: var(--button-bg) !important;
            color: white !important;
        }}

        .stButton>button:hover {{
            background-color: var(--button-hover) !important;
        }}

        .custom-card {{
            background: var(--secondary-bg) !important;
            border: 1px solid var(--border-color) !important;
        }}

        .student-card {{
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            background: var(--secondary-bg);
            border: 1px solid var(--border-color);
        }}

        .stepper-container div[data-tooltip] {{
            margin: 0 1.5rem;
        }}

        @media (max-width: 768px) {{
            .stColumn {{
                flex-direction: column !important;
            }}
        }}

        [data-high-contrast="true"] {{
            filter: contrast(1.4);
        }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="github-corner">
        <a href="https://github.com/antongandersson" target="_blank">
            <svg width="80" height="80" viewBox="0 0 250 250" style="fill:#3b82f6; color:#fff; position: absolute; top: 0; border: 0; right: 0;">
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