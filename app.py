import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

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
        
        # Gensidige førstevalg
        if student2.id in student1.preferred_partners[:1] and student1.id in student2.preferred_partners[:1]:
            score += 10.0
        # Gensidige valg
        elif student2.id in student1.preferred_partners and student1.id in student2.preferred_partners:
            score += 5.0
        # Ensidigt valg
        elif student2.id in student1.preferred_partners or student1.id in student2.preferred_partners:
            score += 2.0
        
        # Matchende primæremne
        if student1.preferred_topic == student2.preferred_topic:
            score += 5.0
        # Sekundær matches
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
        used_topics = set()

        while unassigned and len(used_topics) < len(self.topics):
            best_group = None
            best_score = -1
            best_topic = None

            # Søg efter bedste gruppe blandt ledige elever
            for size in range(2, min(self.max_group_size + 1, len(unassigned) + 1)):
                for members in self._get_possible_groups(list(unassigned), size):
                    if not members:
                        continue
                    
                    # Beregn gruppescore og find potentielt emne
                    score = self._calculate_group_score(members, score_matrix)
                    topic_counts = {}
                    
                    for i in members:
                        topic = self.students[i].preferred_topic
                        if topic and topic not in used_topics:
                            topic_counts[topic] = topic_counts.get(topic, 0) + 1

                    if not topic_counts:
                        continue  # Spring over grupper uden gyldigt emne
                    
                    current_topic = max(topic_counts.items(), key=lambda x: x[1])[0]
                    
                    # Opdater bedste gruppe hvis højere score eller bedre emnematch
                    if score > best_score or (score == best_score and len(members) > len(best_group)):
                        best_score = score
                        best_group = members
                        best_topic = current_topic

            if best_group and best_topic:
                used_topics.add(best_topic)
                group_members = [self.students[i] for i in best_group]
                groups.append(Group(group_members, best_topic, best_score))
                unassigned -= set(best_group)
            else:
                break  # Stop hvis ingen gyldige grupper kan dannes

        # Håndter resterende elever
        if unassigned:
            remaining_students = [self.students[i] for i in unassigned]
            available_topics = [t for t in self.topics if t not in used_topics]
            chosen_topic = available_topics[0] if available_topics else "Ingen tilgængeligt emne"
            groups.append(Group(remaining_students, chosen_topic, 0.0))

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

def go_to_setup():
    st.session_state.page = 'setup'
    st.session_state.setup_complete = False

def go_to_main():
    st.session_state.page = 'main'
    st.session_state.setup_complete = True

def display_student_status(system: GroupFormationSystem, preferences_set: set):
    st.subheader("Elevstatus")
    cols = st.columns(5)
    for i, student in enumerate(system.students):
        col_index = i % 5
        with cols[col_index]:
            if student.id in preferences_set:
                st.markdown(f"✅ {student.name}")
            else:
                st.markdown(f"⭕ {student.name}")

def setup_page():
    st.title("Gruppedannelsessystem - Konfiguration")
    
    with st.form("setup_form"):
        st.subheader("Grundindstillinger")
        num_students = st.number_input(
            "Antal elever", 
            min_value=2, 
            max_value=100, 
            value=st.session_state.num_students
        )
        num_topics = st.number_input(
            "Antal emner", 
            min_value=1, 
            max_value=20, 
            value=len(st.session_state.topics)
        )
        
        st.subheader("Emnekonfiguration")
        topics = []
        cols = st.columns(3)
        for i in range(num_topics):
            with cols[i % 3]:
                default_topic = st.session_state.topics[i] if i < len(st.session_state.topics) else f"Emne {i+1}"
                topic = st.text_input(f"Emne {i+1}", value=default_topic)
                topics.append(topic)
        
        st.subheader("Elevnavne")
        student_names = []
        cols = st.columns(5)
        for i in range(num_students):
            with cols[i % 5]:
                default_name = st.session_state.student_names[i] if i < len(st.session_state.student_names) else f"Elev {i+1}"
                name = st.text_input(f"Elev {i+1}", value=default_name)
                student_names.append(name)
        
        if st.form_submit_button("Start konfiguration"):
            st.session_state.num_students = num_students
            st.session_state.topics = topics
            st.session_state.student_names = student_names
            st.session_state.system = GroupFormationSystem(num_students, topics, student_names)
            st.session_state.preferences_set = set()
            go_to_main()
            st.rerun()

def main_page():
    st.title("Gruppedannelsessystem")
    
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
    
    st.sidebar.header("Elevvælger")
    selected_student_id = st.sidebar.selectbox(
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
        st.success(f"Valg gemt for {st.session_state.system.students[selected_student_id-1].name}")
        st.rerun()
    
    st.subheader("Samlet status")
    progress = len(st.session_state.preferences_set) / len(st.session_state.system.students)
    st.progress(progress)
    st.write(f"{len(st.session_state.preferences_set)}/{len(st.session_state.system.students)} elever har indsendt valg")
    
    if st.button("🔄 Dan grupper"):
        with st.spinner("Danner grupper..."):
            score_matrix = st.session_state.system.create_score_matrix()
            groups = st.session_state.system.find_best_groups(score_matrix)
            
            st.subheader("Resultater")
            for i, group in enumerate(groups, 1):
                with st.expander(f"Gruppe {i}: {group.topic} (Score: {group.score:.1f})", expanded=i==1):
                    st.write(f"**Antal medlemmer:** {len(group.members)}")
                    st.write("**Elever:**")
                    for member in group.members:
                        st.write(f"- {member.name}")
            
            st.subheader("Statistik")
            col1, col2, col3 = st.columns(3)
            total_matched = sum(len(g.members) for g in groups)
            col1.metric("Grupper dannet", len(groups))
            col2.metric("Elever placeret", f"{total_matched}/{len(st.session_state.system.students)}")
            col3.metric("Gns. gruppescore", f"{sum(g.score for g in groups)/len(groups):.1f}" if groups else "0.0")
            
            if total_matched < len(st.session_state.system.students):
                st.warning(f"{len(st.session_state.system.students) - total_matched} elever kunne ikke placeres")

def main():
    initialize_session_state()
    if st.session_state.page == 'setup':
        setup_page()
    else:
        main_page()

if __name__ == "__main__":
    main()