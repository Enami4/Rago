import streamlit as st
import pandas as pd
from PIL import Image
import PyPDF2
import pdf2image
import io
import base64
import json
from datetime import datetime
import bcrypt
from dotenv import load_dotenv
import os
from openai import OpenAI
from streamlit_option_menu import option_menu

load_dotenv()

st.set_page_config(
    page_title="Document AI Extractor - OGAR",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'users' not in st.session_state:
    st.session_state.users = {}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = []

# Use OGAR_API_key from .env file
api_key = os.getenv('OGAR_API_key') or os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# Default comprehensive prompt for OGAR insurance template
DEFAULT_OGAR_PROMPT = """Extract ALL fields from this insurance document (OGAR template) in French. 
Return a detailed JSON object with the following structure:

{
  "informations_compagnie": {
    "nom_compagnie": "",
    "telephone": "",
    "fax": "",
    "bp": "",
    "email": "",
    "courtier": ""
  },
  "informations_police": {
    "police_numero": "",
    "quittance_numero": "",
    "emission_date": "",
    "effet_du": "",
    "effet_heure": "",
    "echeance_au": "",
    "echeance_heure": "",
    "compagnie": "",
    "affaire": ""
  },
  "designation_vehicule": {
    "marque": "",
    "genre": "",
    "type": "",
    "carrosserie": "",
    "energie": "",
    "puissance": "",
    "nombre_places": "",
    "valeur_neuve": "",
    "valeur_venale": "",
    "mise_circulation": "",
    "immatriculation": "",
    "chassis": "",
    "usage": ""
  },
  "souscripteur": {
    "nom": "",
    "bp": "",
    "ville": "",
    "pays": "",
    "telephone": "",
    "fax": "",
    "numero_client": ""
  },
  "assure": {
    "nom": "",
    "bp": "",
    "ville": "",
    "pays": "",
    "telephone": "",
    "fax": ""
  },
  "garanties": {
    "risque_a_responsabilite_civile": {"valeur": "", "prime": ""},
    "risque_b_recours_tiers_incendie": {"valeur": "", "prime": ""},
    "risque_c_defense_recours": {"valeur": "", "prime": ""},
    "risque_d_avance_recours": {"valeur": "", "prime": ""},
    "risque_e_incendie": {"valeur": "", "prime": ""},
    "risque_f_vol": {"valeur": "", "prime": ""},
    "risque_g_vol_agression": {"valeur": "", "prime": ""},
    "risque_h_bris_glace": {"valeur": "", "prime": ""},
    "risque_i_perte_totale": {"valeur": "", "prime": ""},
    "risque_j_tierce_collision": {"valeur": "", "prime": ""},
    "risque_k_dommages": {"valeur": "", "prime": ""},
    "risque_l_nombre_passagers": {"valeur": "", "prime": ""},
    "risque_m_pt_camion": {"valeur": "", "prime": ""},
    "risque_n_pt_eleves": {"valeur": "", "prime": ""},
    "risque_o_passagers_clandestins": {"valeur": "", "prime": ""},
    "risque_p_remorque": {"valeur": "", "prime": ""},
    "risque_q_individuelle_passagers": {"valeur": "", "prime": ""},
    "risque_r_assistance": {"valeur": "", "prime": ""}
  },
  "tarif": {
    "bonus": "",
    "taux_pourcent": "",
    "montant": "",
    "stat_auto": "",
    "stat_ip": ""
  },
  "capitaux": {
    "deces": "",
    "ipp": "",
    "frais_medicaux": ""
  },
  "primes_detail": {
    "prime_nette_brute": "",
    "reductions": "",
    "prime_nette_reduite_deduites": "",
    "accessoires": "",
    "taxes": "",
    "cemac": "",
    "css": "",
    "tsvl": "",
    "cca": "",
    "prime_totale": ""
  }
}

Extract every field visible in the document. If a field is empty or not visible, use an empty string "". Be precise and accurate."""

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def flatten_json_to_two_columns(data, parent_key=''):
    """
    Flatten nested JSON and convert to two-column format:
    Column 1: Nom du champ (Field name)
    Column 2: Valeur du champ (Field value)
    """
    items = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                # If it's a nested dict, recursively flatten
                items.extend(flatten_json_to_two_columns(value, new_key))
            elif isinstance(value, list):
                # If it's a list, convert to string
                items.append({
                    'Nom du champ': new_key,
                    'Valeur du champ': ', '.join(map(str, value)) if value else ''
                })
            else:
                # Simple value
                items.append({
                    'Nom du champ': new_key,
                    'Valeur du champ': str(value) if value is not None else ''
                })
    else:
        items.append({
            'Nom du champ': parent_key,
            'Valeur du champ': str(data) if data is not None else ''
        })
    
    return items

def extract_data_from_image(image, prompt=DEFAULT_OGAR_PROMPT):
    base64_image = encode_image(image)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using latest model for better accuracy
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        result = response.choices[0].message.content
        try:
            # Try to parse as JSON
            json_data = json.loads(result)
            return json_data
        except:
            # If not valid JSON, try to extract JSON from markdown code blocks
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                return {"raw_text": result}
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def pdf_to_images(pdf_file):
    images = []
    try:
        pdf_bytes = pdf_file.read()
        images = pdf2image.convert_from_bytes(pdf_bytes, dpi=200)
        return images
    except Exception as e:
        st.error(f"Error converting PDF: {str(e)}")
        return []

def signup_page():
    st.title("📝 Sign Up")
    
    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username")
            email = st.text_input("Email")
        
        with col2:
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
        
        submit = st.form_submit_button("Sign Up", use_container_width=True)
        
        if submit:
            if not username or not email or not password:
                st.error("Please fill all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif username in st.session_state.users:
                st.error("Username already exists")
            else:
                st.session_state.users[username] = {
                    'email': email,
                    'password': hash_password(password)
                }
                st.success("Account created successfully! Please login.")
                st.session_state.page = 'login'
                st.rerun()

def login_page():
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if username in st.session_state.users:
                if verify_password(password, st.session_state.users[username]['password']):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid password")
            else:
                st.error("Username not found")

def main_app():
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}!")
        
        st.markdown("### 📋 About")
        st.info("This app extracts data from OGAR insurance documents using AI.")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.extracted_data = []
            st.rerun()
    
    st.title("📄 OGAR Document AI Extractor")
    st.markdown("Upload OGAR insurance documents (images or PDFs) to extract structured data")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "📤 Drag and drop or browse files",
            type=['png', 'jpg', 'jpeg', 'pdf'],
            accept_multiple_files=True,
            help="Upload OGAR insurance document images or PDF files"
        )
        
        use_custom_prompt = st.checkbox("Use custom extraction prompt", value=False)
        
        if use_custom_prompt:
            custom_prompt = st.text_area(
                "Custom extraction prompt",
                value=DEFAULT_OGAR_PROMPT,
                height=200,
                help="Modify the default prompt if needed"
            )
        else:
            custom_prompt = DEFAULT_OGAR_PROMPT
            st.info("✅ Using default OGAR template extraction prompt")
    
    with col2:
        st.markdown("### ⚙️ Extraction Settings")
        st.markdown("""
        **Default extraction includes:**
        - Company information
        - Policy details
        - Vehicle designation
        - Subscriber & insured info
        - All coverage/warranties
        - Premium breakdown
        - All fees and taxes
        """)
    
    if uploaded_files:
        if st.button("🚀 Extract Data", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            st.session_state.extracted_data = []
            
            for idx, file in enumerate(uploaded_files):
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
                if file.type == "application/pdf":
                    with st.spinner(f"Processing {file.name}..."):
                        images = pdf_to_images(file)
                        for img_idx, image in enumerate(images):
                            data = extract_data_from_image(image, custom_prompt)
                            if data:
                                data['_metadata'] = {
                                    'source_file': file.name,
                                    'page': img_idx + 1,
                                    'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                st.session_state.extracted_data.append(data)
                else:
                    with st.spinner(f"Processing {file.name}..."):
                        image = Image.open(file)
                        data = extract_data_from_image(image, custom_prompt)
                        if data:
                            data['_metadata'] = {
                                'source_file': file.name,
                                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            st.session_state.extracted_data.append(data)
            
            st.success(f"✅ Successfully extracted data from {len(uploaded_files)} file(s)!")
    
    if st.session_state.extracted_data:
        st.markdown("---")
        st.markdown("### 📊 Extracted Data")
        
        tab1, tab2, tab3 = st.tabs(["Two-Column View", "Table View", "JSON View"])
        
        with tab1:
            st.markdown("#### Structured Field-Value Format")
            for idx, data in enumerate(st.session_state.extracted_data):
                metadata = data.pop('_metadata', {})
                st.markdown(f"**📄 File: {metadata.get('source_file', 'Unknown')}**")
                if 'page' in metadata:
                    st.markdown(f"*Page: {metadata['page']}*")
                
                # Flatten the JSON to two columns
                flattened_data = flatten_json_to_two_columns(data)
                df_two_col = pd.DataFrame(flattened_data)
                
                st.dataframe(df_two_col, use_container_width=True, height=400)
                st.markdown("---")
        
        with tab2:
            st.markdown("#### Full Table View")
            all_flattened = []
            for data in st.session_state.extracted_data:
                metadata = data.pop('_metadata', {})
                flattened = flatten_json_to_two_columns(data)
                for item in flattened:
                    item['Source File'] = metadata.get('source_file', 'Unknown')
                    if 'page' in metadata:
                        item['Page'] = metadata['page']
                all_flattened.extend(flattened)
            
            df_full = pd.DataFrame(all_flattened)
            st.dataframe(df_full, use_container_width=True)
        
        with tab3:
            st.markdown("#### Raw JSON Data")
            st.json(st.session_state.extracted_data)
        
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # Prepare Excel download with two-column format
            all_data_for_excel = []
            
            for data in st.session_state.extracted_data:
                metadata = data.get('_metadata', {})
                data_copy = {k: v for k, v in data.items() if k != '_metadata'}
                
                flattened = flatten_json_to_two_columns(data_copy)
                
                # Add metadata columns
                for item in flattened:
                    item['Fichier source'] = metadata.get('source_file', 'Unknown')
                    if 'page' in metadata:
                        item['Page'] = metadata.get('page', '')
                    item['Date extraction'] = metadata.get('extraction_date', '')
                
                all_data_for_excel.extend(flattened)
            
            df_excel = pd.DataFrame(all_data_for_excel)
            # Reorder columns to put metadata at the end
            cols = ['Nom du champ', 'Valeur du champ', 'Fichier source']
            if 'Page' in df_excel.columns:
                cols.append('Page')
            cols.append('Date extraction')
            df_excel = df_excel[cols]
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_excel.to_excel(writer, sheet_name='Données OGAR', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Données OGAR']
                for idx, col in enumerate(df_excel.columns):
                    max_length = max(
                        df_excel[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            st.download_button(
                label="📥 Download Excel File",
                data=buffer.getvalue(),
                file_name=f"ogar_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.button("🗑️ Clear Data", use_container_width=True):
                st.session_state.extracted_data = []
                st.rerun()

def main():
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    
    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            tab1, tab2 = st.tabs(["Login", "Sign Up"])
            
            with tab1:
                login_page()
            
            with tab2:
                signup_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
