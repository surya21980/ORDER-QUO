import streamlit as st
import pandas as pd
import gspread
import pytz
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI ---
SHEET_ID_ORDER = "1yRWMfWtA39Ookk-f8jptaUX86CUm4SRKOAVQ_2_af8o"
SCOPE = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Caching: Data hanya diambil dari Google tiap 10 menit untuk menghemat kuota
@st.cache_data(ttl=600)
def fetch_all_data(tab_name):
    creds_dict = dict(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID_ORDER).worksheet(tab_name)
    return sheet.get_all_values()

def update_sheet(tab_name, data):
    # Fungsi khusus untuk update data ke Google Sheets
    creds_dict = dict(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID_ORDER).worksheet(tab_name)
    sheet.clear()
    sheet.append_rows(data)
    st.cache_data.clear() # Reset cache setelah update agar data baru muncul

def get_wita_time():
    return datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y %H:%M")

def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        # ... (Logika Login tetap sama seperti sebelumnya) ...
        return

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Input Kosong", "🛒 Input Inden", "📄 Lap. Kosong", "📋 Lap. Inden"])

    # --- TAB 1 & 2: INPUT (Gunakan sheet.append_row, ini sangat hemat API) ---
    with tab1:
        st.header("Input Barang Kosong")
        # ... (Logika Input data menggunakan sheet.append_row) ...
        # Tambahkan st.cache_data.clear() setelah simpan

    # --- TAB 3: LAPORAN KOSONG ---
    with tab3:
        st.header("📦 Laporan Barang Kosong")
        val = fetch_all_data("BARANG_KOSONG")
        if len(val) > 1:
            df = pd.DataFrame(val[1:], columns=val[0])
            df["DONE ORDER"] = df["DONE ORDER"].str.upper() == 'TRUE'
            p_df = df[df["DONE ORDER"] == False].reset_index(drop=True); p_df.index += 1
            d_df = df[df["DONE ORDER"] == True].reset_index(drop=True); d_df.index += 1
            
            st.subheader("⏳ Pending"); st.dataframe(p_df, use_container_width=True)
            with st.expander("✏️ Update Status"):
                with st.form("edit_k"):
                    edit_p = st.data_editor(p_df, column_config={"DONE ORDER": st.column_config.CheckboxColumn()})
                    if st.form_submit_button("Update"):
                        final_df = pd.concat([edit_p, d_df])
                        # Siapkan data untuk di-append
                        data_to_upload = [val[0]] + final_df.astype(str).values.tolist()
                        update_sheet("BARANG_KOSONG", data_to_upload)
                        st.rerun()
            st.subheader("✅ Done"); st.dataframe(d_df, use_container_width=True)

    # --- TAB 4: LAPORAN INDEN ---
    with tab4:
        st.header("🛒 Laporan Barang Inden")
        val = fetch_all_data("BARANG_INDEN")
        if len(val) > 1:
            df = pd.DataFrame(val[1:], columns=val[0])
            df["DONE ORDER"] = df["DONE ORDER"].str.upper() == 'TRUE'
            df["SAMPAI"] = df["SAMPAI"].str.upper() == 'TRUE'
            mask = (df["DONE ORDER"] == False) | (df["SAMPAI"] == False)
            p_df = df[mask].reset_index(drop=True); p_df.index += 1
            d_df = df[~mask].reset_index(drop=True); d_df.index += 1
            
            st.subheader("⏳ Pending"); st.dataframe(p_df, use_container_width=True)
            with st.expander("✏️ Update Status"):
                with st.form("edit_i"):
                    edit_p = st.data_editor(p_df, column_config={"DONE ORDER": st.column_config.CheckboxColumn(), "SAMPAI": st.column_config.CheckboxColumn()})
                    if st.form_submit_button("Update"):
                        final_df = pd.concat([edit_p, d_df])
                        data_to_upload = [val[0]] + final_df.astype(str).values.tolist()
                        update_sheet("BARANG_INDEN", data_to_upload)
                        st.rerun()
            st.subheader("✅ Done"); st.dataframe(d_df, use_container_width=True)