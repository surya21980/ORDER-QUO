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

    # Ambil data dari Secrets
    try:
        SHEET_URL = st.secrets["SHEET_URL"]
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

        @st.cache_data(ttl=600)
        def load_data():
            df = pd.read_csv(SHEET_URL)
            df.columns = df.columns.str.strip()
            return df

        df = load_data()
        st.markdown(f"### Data berhasil dimuat: :red[{len(df)}]")
        
        tab1, tab2, tab3 = st.tabs(["🛒 Penawaran (Sales)", "📊 Manajemen (Direksi)", "📸 Cari dari Gambar"])

        # --- TAB 1: AREA SALES ---
        with tab1:
            st.subheader("Area Pencarian Penawaran")
            search_sales = st.text_input("🔍 Cari PN atau Keterangan [(,) (;) untuk banyak]:", key="s_sales")
            if search_sales:
                queries = [q.strip() for q in re.split(r'[;,]', search_sales) if q.strip()]
                df_sales = df[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA', 'BARIS KE', 'TANGGAL UPDATE']]
                filtered = df_sales[df_sales.apply(lambda row: any(any(str(q).lower() in str(cell).lower() for q in queries) for cell in row), axis=1)]
                if not filtered.empty:
                    st.dataframe(filtered, use_container_width=True, hide_index=True)
                    st.text_area("Copy tabel untuk Excel/WA:", value=filtered[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA']].to_csv(index=False, sep='\t'), height=150)
                else: st.warning("Data tidak ditemukan.")

        # --- TAB 2: AREA DIREKSI ---
        with tab2:
            st.subheader("📊 Area Manajemen Direksi")
            if 'logged_in_db' not in st.session_state: st.session_state.logged_in_db = False
            if not st.session_state.logged_in_db:
                if st.text_input("Password Direksi:", type="password") == "Admin123": st.session_state.logged_in_db = True; st.rerun()
            else:
                if st.button("Logout"): st.session_state.logged_in_db = False; st.rerun()
                search_dir = st.text_input("🔍 Cari data internal:", key="s_dir")
                df_dir = df[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA', 'MODAL', 'SUPPLIER', 'ALTER']]
                if search_dir:
                    st.dataframe(df_dir[df_dir.apply(lambda row: row.astype(str).str.contains(search_dir, case=False).any(), axis=1)], use_container_width=True, hide_index=True)
                else: st.dataframe(df_dir, use_container_width=True, hide_index=True)

        # --- TAB 3: CARI DARI GAMBAR ---
        with tab3:
            st.subheader("📸 Cari Barang via Gambar")
            
            # Simpan gambar di session_state agar tidak hilang saat tombol ditekan
            if 'pasted_image' not in st.session_state: st.session_state.pasted_image = None
            
            paste_result = paste_image_button(label="📋 Paste Gambar dari Clipboard")
            if paste_result.image_data is not None:
                st.session_state.pasted_image = paste_result.image_data
            
            if st.session_state.pasted_image is not None:
                st.image(st.session_state.pasted_image, width=300)
                if st.button("Proses Gambar"):
                    with st.spinner("AI sedang membaca..."):
                        img_byte_arr = io.BytesIO()
                        st.session_state.pasted_image.save(img_byte_arr, format='PNG')
                        image_part = types.Part.from_bytes(data=img_byte_arr.getvalue(), mime_type='image/png')
                        
                        response = client.models.generate_content(
                            model="gemini-flash-lite-latest",
                            contents=[image_part, "Tampilkan daftar PN atau kata kunci saja, dipisah koma. Hanya teks."]
                        )
                        hasil_pn = response.text.replace('\n', ', ')
                        st.write(f"PN terbaca: **{hasil_pn}**")
                        
                        queries = [q.strip() for q in re.split(r'[;,]', hasil_pn) if q.strip()]
                        filtered = df[df.apply(lambda row: any(any(str(q).lower() in str(cell).lower() for q in queries) for cell in row), axis=1)]
                        
                        if not filtered.empty:
                            st.dataframe(filtered[['PART NUMBER', 'KETERANGAN', 'MEREK', 'HARGA']], use_container_width=True, hide_index=True)
                        else: st.warning("Data tidak ditemukan.")
    except Exception as e:
        st.error(f"Error Database: {e}")