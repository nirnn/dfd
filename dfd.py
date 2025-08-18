import streamlit as st
from openai import OpenAI
from typing import List, Dict, Optional
import json
import os

def is_streamlit_cloud():
    return os.environ.get("STREAMLIT_RUNTIME") == "cloud"

if is_streamlit_cloud():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Categories for appointment triage
APPOINTMENT_CATEGORIES = {
    1: "מנהלי - בקשה לטופס 17, סיכום רפואי וכו'",
    2: "לא לרופא משפחה - חיסונים לנסיעה וכו'",
    3: "קליני - אבל ניתן לפתור בדרך אחרת",
    4: "קליני - צריך רופא משפחה"
}

def read_system_prompt():
    with open('dfd_system_prompt.txt', 'r', encoding='utf-8') as file:
        file_content = file.read()
    return file_content
SYSTEM_PROMPT = read_system_prompt()

def load_css():
    """Load CSS from external file"""
    try:
        with open("hebrew_rtl_styles.css", "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("לא נמצא קובץ הסגנון hebrew_rtl_styles.css")
        # Fallback to basic RTL support
        st.markdown("""
        <style>
        .main .block-container {
            direction: rtl;
            text-align: right;
        }
        .stMarkdown {
            direction: rtl;
            text-align: right;
        }
        </style>
        """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "categorization_complete" not in st.session_state:
        st.session_state.categorization_complete = False
    if "final_category" not in st.session_state:
        st.session_state.final_category = None

def call_openai_api(messages: List[Dict[str, str]]) -> Optional[str]:
    """Call OpenAI API with error handling"""
    try:
        response = client.chat.completions.create(
            model= "gpt-4.1-2025-04-14", #"gpt-4",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"שגיאה בקריאה ל-OpenAI API: {str(e)}")
        return None

def extract_categorization(response: str) -> Optional[Dict]:
    """Extract JSON categorization from response"""
    try:
        # Look for JSON in the response
        if "{" in response and "}" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            categorization = json.loads(json_str)
            
            # Ensure category is an integer and within valid range
            if "category" in categorization:
                category = categorization["category"]
                # Convert string to int if needed
                if isinstance(category, str):
                    try:
                        category = int(category)
                    except ValueError:
                        return None
                
                # Validate category is in valid range
                if category not in APPOINTMENT_CATEGORIES:
                    return None
                
                categorization["category"] = category
                return categorization
    except Exception as e:
        print(f"Error parsing categorization: {e}")
        pass
    return None

def display_final_result(category: int, reason: str):
    """Display the final categorization result"""
    st.success("✅ הסיבה לתור זוהתה בהצלחה!")
    
    # Validate category and provide fallback
    if category not in APPOINTMENT_CATEGORIES:
        st.error(f"שגיאה: קטגוריה לא תקינה ({category})")
        return
    
    category_colors = {
        1: "blue",
        2: "orange", 
        3: "green",
        4: "red"
    }
    
    category_description = APPOINTMENT_CATEGORIES.get(category, "קטגוריה לא ידועה")
    
    st.markdown(f"""
    <div class="rtl">
    
    ### תוצאה:
    **קטגוריה:** :{category_colors.get(category, 'gray')}[{category_description}]
    
    **הסבר:** {reason}
    
    </div>
    """, unsafe_allow_html=True)
    
    # Provide next steps based on category
    if category == 1:
        st.info("💡 **הצעה:** פנה למזכירות הקליניקה לבקשות מנהליות")
    elif category == 2:
        st.info("💡 **הצעה:** פנה לאחות הקליניקה או למרכז חיסונים")
    elif category == 3:
        st.info("💡 **הצעה:** נסה ייעוץ טלפוני עם האחות או פנה לרוקח")
    elif category == 4:
        st.info("💡 **הצעה:** קבע תור לרופא המשפחה")
    else:
        st.warning("לא ניתן לספק המלצה עבור קטגוריה זו")

def main():
    st.set_page_config(
        page_title="מערכת ייעוץ לתורים - רופא משפחה",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Load RTL CSS support for Hebrew
    load_css()
    
    # Header
    st.markdown('<div class="rtl">', unsafe_allow_html=True)
    st.title("🩺 מערכת ייעוץ לתורים - רופא משפחה")
    st.markdown("**מה הסיבה לבקשת התור לרופא המשפחה?**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    initialize_session_state()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(f'<div class="rtl">{message["content"]}</div>', unsafe_allow_html=True)
    
    # Show final result if categorization is complete
    if st.session_state.categorization_complete and st.session_state.final_category:
        display_final_result(
            st.session_state.final_category["category"],
            st.session_state.final_category["reason"]
        )
    
    # Chat input
    if not st.session_state.categorization_complete:
        if prompt := st.chat_input("תאר/י את הסיבה לתור..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(f'<div class="rtl">{prompt}</div>', unsafe_allow_html=True)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("מעבד..."):
                    response = call_openai_api(st.session_state.messages)
                    
                    if response:
                        # Check if this is a final categorization
                        categorization = extract_categorization(response)
                        
                        if categorization and "category" in categorization and "reason" in categorization:
                            # Validate that we have both required fields
                            category = categorization.get("category")
                            reason = categorization.get("reason", "לא סופק הסבר")
                            
                            if category in APPOINTMENT_CATEGORIES:
                                # Final categorization received
                                st.session_state.categorization_complete = True
                                st.session_state.final_category = categorization
                                st.rerun()
                            else:
                                # Invalid category, continue conversation
                                st.markdown(f'<div class="rtl">{response}</div>', unsafe_allow_html=True)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                        else:
                            # Continue conversation
                            st.markdown(f'<div class="rtl">{response}</div>', unsafe_allow_html=True)
                            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        # Reset button
        if st.button("🔄 התחל שיחה חדשה", type="primary"):
            st.session_state.messages = []
            st.session_state.categorization_complete = False
            st.session_state.final_category = None
            st.rerun()
    
    # Sidebar with instructions
    with st.sidebar:
        st.markdown("""
        <div class="rtl">
        
        ### הוראות שימוש
        
        1. תאר את הסיבה לבקשת התור
        2. המערכת תשאל שאלות מבהירות אם נדרש
        3. בסוף תקבל המלצה לגבי סוג הטיפול המתאים
        
        ### קטגוריות
        
        </div>
        """, unsafe_allow_html=True)
        
        for num, desc in APPOINTMENT_CATEGORIES.items():
            st.markdown(f'<div class="rtl"><strong>{num}.</strong> {desc}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()