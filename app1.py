import streamlit as st
import pandas as pd
import re
import requests
import io
from google import genai
from google.genai import types
from streamlit_paste_button import paste_image_button

def main():
    st.title("📦 Sistem Database Terpadu")

    # Load Data
    try:
        SHEET_URL = st.secrets["SHEET_URL"]
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

        @st.cache_data(ttl=600)
        def load_data():
            df = pd.read_csv(SHEET_URL)
            df.columns = df.columns.str.strip()
            return df
        df = load_data()
    except Exception as e:
        st.error(f"Error Loading Data: {e}"); return

    # --- NAVIGASI MODUL ---
    tab_list = ["🛒 Penawaran (Sales)", "📊 Manajemen (Direksi)", "📸 Cari dari Gambar"]
    selected_tab = st.sidebar.radio("Pilih Modul:", tab_list)

    # --- TAB 1: AREA SALES ---
    if selected_tab == "🛒 Penawaran (Sales)":
        st.subheader("Area Pencarian Penawaran")
        with st.form("search_sales_form"):
            search_sales = st.text_input("🔍 Cari PN atau Keterangan [(,) (;) untuk banyak]:")
            submitted = st.form_submit_button("Cari")
        
        if submitted and search_sales:
            queries = [q.strip() for q in re.split(r'[;,]', search_sales) if q.strip()]
            df_sales = df[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA', 'BARIS KE', 'TANGGAL UPDATE']]
            filtered = df_sales[df_sales.apply(lambda row: any(any(str(q).lower() in str(cell).lower() for q in queries) for cell in row), axis=1)]
            
            if not filtered.empty:
                st.dataframe(filtered, use_container_width=True, hide_index=True)
                df_copy = filtered[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA']]
                st.text_area("Copy tabel untuk Excel/WA:", value=df_copy.to_csv(index=False, sep='\t'), height=150)
            else: st.warning("Data tidak ditemukan.")
            
            not_found = [q for q in queries if not df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1).any()]
            if not_found:
                st.error(f"Peringatan: Item tidak ditemukan: **{', '.join(not_found)}**")
                try:
                    requests.get(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage?chat_id={st.secrets['TELEGRAM_CHAT_ID']}&text=⚠️ Sales (Text): {', '.join(not_found)}")
                except: pass

    # --- TAB 2: AREA DIREKSI ---
    elif selected_tab == "📊 Manajemen (Direksi)":
        st.subheader("📊 Area Manajemen Direksi")
        if 'logged_in_db' not in st.session_state: st.session_state.logged_in_db = False
        
        if not st.session_state.logged_in_db:
            password = st.text_input("Masukkan Password Direksi:", type="password", key="pass_input")
            if password == "Admin123": st.session_state.logged_in_db = True; st.rerun()
            elif password: st.error("Password Salah!")
        
        if st.session_state.logged_in_db:
            if st.button("Logout"): st.session_state.logged_in_db = False; st.rerun()
            
            search_dir = st.text_input("🔍 Cari data internal (PN/Keterangan/Supplier) [(,) (;) untuk banyak]:", key="s_dir")
            df_dir = df[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA', 'MODAL', 'SUPPLIER', 'ALTER']]
            
            if search_dir:
                queries = [q.strip() for q in re.split(r'[;,]', search_dir) if q.strip()]
                filtered_dir = df_dir[df_dir.apply(lambda row: any(any(str(q).lower() in str(cell).lower() for q in queries) for cell in row), axis=1)]
                if not filtered_dir.empty: st.dataframe(filtered_dir, use_container_width=True, hide_index=True)
                else: st.warning("Data tidak ditemukan.")
                
                not_found = [q for q in queries if not df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1).any()]
                if not_found:
                    st.error(f"Peringatan: Item tidak ditemukan: **{', '.join(not_found)}**")
                    try:
                        requests.get(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage?chat_id={st.secrets['TELEGRAM_CHAT_ID']}&text=⚠️ Direksi mencari: {', '.join(not_found)}")
                    except: pass
            else: st.dataframe(df_dir, use_container_width=True, hide_index=True)

    # --- TAB 3: CARI DARI GAMBAR ---
    elif selected_tab == "📸 Cari dari Gambar":
        st.subheader("📸 Cari Barang via Gambar")
        if 'pasted_image' not in st.session_state: st.session_state.pasted_image = None
        paste_result = paste_image_button(label="📋 Paste Gambar dari Clipboard")
        if paste_result.image_data is not None: st.session_state.pasted_image = paste_result.image_data
        
        if st.session_state.pasted_image is not None:
            st.image(st.session_state.pasted_image, width=300)
            with st.form("image_form"):
                btn_proses = st.form_submit_button("Proses Gambar")
            
            if btn_proses:
                with st.spinner("AI sedang membaca..."):
                    img_byte_arr = io.BytesIO()
                    st.session_state.pasted_image.save(img_byte_arr, format='PNG')
                    image_part = types.Part.from_bytes(data=img_byte_arr.getvalue(), mime_type='image/png')
                    response = client.models.generate_content(model="gemini-flash-lite-latest", contents=[image_part, "Tampilkan daftar PN dipisah koma. Hanya teks."])
                    
                    hasil_pn = response.text.replace('\n', ', ')
                    st.write(f"PN terbaca: **{hasil_pn}**")
                    queries = [q.strip() for q in re.split(r'[;,]', hasil_pn) if q.strip()]
                    filtered = df[df.apply(lambda row: any(any(str(q).lower() in str(cell).lower() for q in queries) for cell in row), axis=1)]
                    
                    if not filtered.empty:
                        st.dataframe(filtered[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA']], use_container_width=True, hide_index=True)
                    else: st.warning("Data tidak ditemukan.")

                    not_found = [q for q in queries if not df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1).any()]
                    if not_found:
                        st.error(f"Peringatan: Item tidak ditemukan: **{', '.join(not_found)}**")
                        try:
                            requests.get(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage?chat_id={st.secrets['TELEGRAM_CHAT_ID']}&text=⚠️ Sales (Gambar): {', '.join(not_found)}")
                        except: pass