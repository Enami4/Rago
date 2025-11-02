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
from anthropic import Anthropic
from streamlit_option_menu import option_menu

load_dotenv()

st.set_page_config(
    page_title="Document OCR Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

if 'users' not in st.session_state:
    # Pre-populate with default user
    default_password = hash_password("Jabe2025!@@")
    st.session_state.users = {
        "Ogar": {
            'email': 'admin@ogar.com',
            'password': default_password
        }
    }
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = []

# Initialize Anthropic client with error handling
api_key = os.getenv('OGAR_API_KEY')
if not api_key:
    st.error("⚠️ Clé API Anthropic non trouvée. Veuillez configurer OGAR_API_KEY dans le fichier .env")
    client = None
else:
    client = Anthropic(api_key=api_key)

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def flatten_json_to_structured_format(data, parent_key='', parent_category=''):
    """
    Flatten nested JSON and convert to structured format:
    Column 1: Categorie (Main category)
    Column 2: Nom du champ (Field name)
    Column 3: Valeur du champ (Field value)
    """
    items = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            # Determine category
            if not parent_category:
                category = key.replace('_', ' ').title()
            else:
                category = parent_category
            
            if isinstance(value, dict):
                # If it's a nested dict, recursively flatten
                items.extend(flatten_json_to_structured_format(value, key, category))
            elif isinstance(value, list):
                # If it's a list, convert to string
                items.append({
                    'Categorie': category,
                    'Nom du champ': key,
                    'Valeur du champ': ', '.join(map(str, value)) if value else ''
                })
            else:
                # Simple value
                items.append({
                    'Categorie': category,
                    'Nom du champ': key,
                    'Valeur du champ': str(value) if value is not None else ''
                })
    else:
        items.append({
            'Categorie': parent_category,
            'Nom du champ': parent_key,
            'Valeur du champ': str(data) if data is not None else ''
        })
    
    return items

def extract_data_from_image(image, prompt="Extract all relevant fields and data from this document. Return as JSON."):
    if not client:
        return None
        
    base64_image = encode_image(image)
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        )
        
        result = response.content[0].text
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
    # Sidebar with logo and user info
    with st.sidebar:
        # Display logo
        try:
            logo = Image.open("ogar_logo.png")
            st.image(logo, use_column_width=True)
        except:
            pass
        
        st.markdown("---")
        st.title(f"👋 Bienvenue, {st.session_state.username}!")
        
        # Information section
        st.markdown("### 📖 Comment fonctionne l'OCR?")
        st.info("""
        1. **Téléchargez** vos documents d'assurance (PDF ou images)
        2. **Extraction automatique** des données avec OCR
        3. **Exportez** en Excel avec tous les champs structurés
        """)
        
        st.markdown("### 🎯 Champs extraits")
        with st.expander("Voir la liste complète"):
            st.markdown("""
            - **Informations compagnie**
            - **Détails de la police**
            - **Véhicule assuré**
            - **Souscripteur & Assuré**
            - **Garanties (18 types)**
            - **Tarifs et primes**
            - **Capitaux et franchises**
            """)
        
        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.extracted_data = []
            st.rerun()
    
    # Main content area
    # Header with logo and title
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        try:
            logo = Image.open("ogar_logo.png")
            st.image(logo, width=100)
        except:
            st.markdown("# 🏢 OGAR")
    
    with col_title:
        st.title("Extracteur Intelligent de Documents d'Assurance")
        st.markdown("### Transformez vos documents OGAR en données structurées")
    
    st.markdown("---")
    
    # Instructions section
    with st.container():
        st.markdown("### 📤 Téléchargez vos documents")
        info_col1, info_col2, info_col3 = st.columns(3)
        
        with info_col1:
            st.info("**📄 Formats acceptés**\nPDF, PNG, JPG, JPEG")
        
        with info_col2:
            st.info("**🔄 Traitement**\nExtraction automatique de tous les champs")
        
        with info_col3:
            st.info("**📊 Export Excel**\nDonnées structurées en 2 colonnes")
    
    st.markdown("---")
    
    # File upload section
    uploaded_files = st.file_uploader(
        "Glissez-déposez vos documents OGAR ou cliquez pour parcourir",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        accept_multiple_files=True,
        help="Téléchargez des images ou des fichiers PDF de vos documents d'assurance OGAR"
    )
    
    # Define the default prompt internally (hidden from user)
    default_prompt = """Extrais TOUS les champs de ce document d'assurance OGAR en français.
Retourne un objet JSON détaillé avec la structure suivante:

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
    "numero_client": "",
    "bp": "",
    "ville": "",
    "pays": "",
    "telephone": "",
    "fax": ""
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
    "risque_a_responsabilite_civile": {"valeur": "", "franchise": "", "prime": ""},
    "risque_b_recours_tiers_incendie": {"valeur": "", "franchise": "", "prime": ""},
    "risque_c_defense_recours": {"valeur": "", "franchise": "", "prime": ""},
    "risque_d_avance_recours": {"valeur": "", "franchise": "", "prime": ""},
    "risque_e_incendie": {"valeur": "", "franchise": "", "prime": ""},
    "risque_f_vol": {"valeur": "", "franchise": "", "prime": ""},
    "risque_g_vol_agression": {"valeur": "", "franchise": "", "prime": ""},
    "risque_h_bris_glace": {"valeur": "", "franchise": "", "prime": ""},
    "risque_i_perte_totale": {"valeur": "", "franchise": "", "prime": ""},
    "risque_j_tierce_collision": {"valeur": "", "franchise": "", "prime": ""},
    "risque_k_dommages": {"valeur": "", "franchise": "", "prime": ""},
    "risque_l_nombre_passagers": {"valeur": "", "franchise": "", "prime": ""},
    "risque_m_pt_camion": {"valeur": "", "franchise": "", "prime": ""},
    "risque_n_pt_eleves": {"valeur": "", "franchise": "", "prime": ""},
    "risque_o_passagers_clandestins": {"valeur": "", "franchise": "", "prime": ""},
    "risque_p_remorque": {"valeur": "", "franchise": "", "prime": ""},
    "risque_q_individuelle_passagers": {"valeur": "", "franchise": "", "prime": ""},
    "risque_r_assistance": {"valeur": "", "franchise": "", "prime": ""}
  },
  "tarif": {
    "bonus": "",
    "taux_pourcent": "",
    "montant": "",
    "stat_auto": "",
    "stat_ip": ""
  },
  "capitaux_individuelle_passager": {
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

Extrais chaque champ visible dans le document. Si un champ est vide ou non visible, utilise une chaîne vide "". 
Sois précis et exhaustif. N'oublie aucun champ."""
    
    if uploaded_files:
        if st.button("🚀 Extraire les données", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            st.session_state.extracted_data = []
            
            for idx, file in enumerate(uploaded_files):
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
                if file.type == "application/pdf":
                    with st.spinner(f"Traitement de {file.name}..."):
                        images = pdf_to_images(file)
                        for img_idx, image in enumerate(images):
                            data = extract_data_from_image(image, default_prompt)
                            if data:
                                data['source_file'] = file.name
                                data['page'] = img_idx + 1
                                st.session_state.extracted_data.append(data)
                else:
                    with st.spinner(f"Traitement de {file.name}..."):
                        image = Image.open(file)
                        data = extract_data_from_image(image, default_prompt)
                        if data:
                            data['source_file'] = file.name
                            st.session_state.extracted_data.append(data)
            
            st.success(f"✅ Données extraites de {len(uploaded_files)} fichier(s)!")
    
    if st.session_state.extracted_data:
        st.markdown("---")
        st.markdown("### 📊 Données extraites")
        
        tab1, tab2 = st.tabs(["Vue tableau", "Vue JSON"])
        
        with tab1:
            # Convert data to table format
            all_fields = []
            for doc in st.session_state.extracted_data:
                source_file = doc.get('source_file', 'Unknown')
                page = doc.get('page', '')
                
                # Create a copy of doc without metadata
                doc_copy = {k: v for k, v in doc.items() if k not in ['source_file', 'page']}
                
                # Flatten the JSON to structured format
                flattened_data = flatten_json_to_structured_format(doc_copy)
                
                # Add metadata to each field
                for item in flattened_data:
                    item['Fichier source'] = source_file
                    if page:
                        item['Page'] = page
                    all_fields.append(item)
            
            if all_fields:
                df = pd.DataFrame(all_fields)
                # Reorder columns
                cols = ['Categorie', 'Nom du champ', 'Valeur du champ', 'Fichier source']
                if 'Page' in df.columns:
                    cols.append('Page')
                df = df[cols]
                st.dataframe(df, use_container_width=True)
        
        with tab2:
            st.json(st.session_state.extracted_data)
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # Convert extracted data to the desired format
            all_fields = []
            
            for doc in st.session_state.extracted_data:
                source_file = doc.get('source_file', 'Unknown')
                page = doc.get('page', '')
                
                # Create a copy of doc without metadata
                doc_copy = {k: v for k, v in doc.items() if k not in ['source_file', 'page']}
                
                # Flatten the JSON to structured format
                flattened_data = flatten_json_to_structured_format(doc_copy)
                
                # Add metadata to each field
                for item in flattened_data:
                    item['Fichier source'] = source_file
                    if page:
                        item['Page'] = page
                
                all_fields.extend(flattened_data)
            
            if all_fields:
                # Create DataFrame with proper column order
                df = pd.DataFrame(all_fields)
                cols = ['Categorie', 'Nom du champ', 'Valeur du champ', 'Fichier source']
                if 'Page' in df.columns:
                    cols.append('Page')
                df = df[cols]
                
                buffer = io.BytesIO()
                
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    # First worksheet: Structured data
                    df.to_excel(writer, sheet_name='Données OGAR', index=False)
                    
                    # Auto-adjust column widths for first worksheet
                    worksheet = writer.sheets['Données OGAR']
                    for idx, col in enumerate(df.columns):
                        max_length = max(
                            df[col].astype(str).apply(len).max(),
                            len(col)
                        )
                        worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
                
                st.download_button(
                    label="📥 Télécharger le fichier Excel",
                    data=buffer.getvalue(),
                    file_name=f"ogar_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
        
        with col2:
            if st.button("🗑️ Effacer les données", use_container_width=True):
                st.session_state.extracted_data = []
                st.rerun()

def main():
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    
    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Display logo at the top of login/signup page
            try:
                logo = Image.open("ogar_logo.png")
                st.image(logo, use_column_width=True)
            except:
                st.markdown("# 🏢 OGAR")
            
            st.markdown("---")
            st.markdown("### Système d'Extraction OCR de Documents")
            st.markdown("---")
            
            tab1, tab2 = st.tabs(["Login", "Sign Up"])
            
            with tab1:
                login_page()
            
            with tab2:
                signup_page()
    else:
        main_app()

if __name__ == "__main__":
    main()