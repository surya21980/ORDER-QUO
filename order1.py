import streamlit as st
import pandas as pd
import gspread
import pytz
import time
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI ---
SHEET_ID_ORDER = "1yRWMfWtA39Ookk-f8jptaUX86CUm4SRKOAVQ_2_af8o"
SCOPE = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

def get_sheet(tab_name):
    # Mengambil kredensial dari Streamlit Secrets
    creds_dict = dict(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    
    # Percobaan akses dengan ID, jika gagal gunakan nama file "orderbook"
    try:
        return client.open_by_key(SHEET_ID_ORDER).worksheet(tab_name)
    except:
        return client.open("orderbook").worksheet(tab_name)

@st.cache_data(ttl=600)
def fetch_all_data(tab_name):
    return get_sheet(tab_name).get_all_values()

def get_wita_time():
    return datetime.now(pytz.timezone('Asia/Makassar')).strftime("%d-%m-%Y %H:%M")

def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'key_k' not in st.session_state: st.session_state.key_k = 0
    if 'key_i' not in st.session_state: st.session_state.key_i = 0

    if not st.session_state.logged_in:
        st.title("🔐 Login")
        user = st.text_input("Username").upper()
        pwd = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if user in ["ADM1", "ADM2", "ADM3", "ADM4", "ADM5", "DIREKSI"] and pwd == "123":
                st.session_state.logged_in = True; st.session_state.user = user; st.rerun()
            else: st.error("Login Gagal!")
        return

    st.sidebar.info(f"User: **{st.session_state.get('user', '')}**")
    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Input Kosong", "🛒 Input Inden", "📄 Lap. Kosong", "📋 Lap. Inden"])

    # --- TAB 1: INPUT KOSONG ---
    with tab1:
        st.header("Input Barang Kosong")
        df_k = pd.DataFrame([{"Part Number": "", "Deskripsi": ""}])
        edit_k = st.data_editor(df_k, key=f"k_{st.session_state.key_k}", num_rows="dynamic", use_container_width=True)
        if st.button("Simpan ke BARANG_KOSONG"):
            data = edit_k[edit_k["Part Number"] != ""]
            if not data.empty:
                sheet = get_sheet("BARANG_KOSONG")
                if len(sheet.get_all_values()) == 0: sheet.append_row(["PART NUMBER", "DESKRIPSI", "TANGGAL INPUT", "INISIAL", "DONE ORDER"])
                for _, r in data.iterrows():
                    sheet.append_row([r["Part Number"], r["Deskripsi"], get_wita_time(), st.session_state.user, "FALSE"])
                st.cache_data.clear(); st.session_state.key_k += 1; st.rerun()

    # --- TAB 2: INPUT INDEN ---
    with tab2:
        st.header("Input Barang Inden")
        df_i = pd.DataFrame([{"Part Number": "", "Deskripsi": "", "QTY": 0, "Customer": "", "Keterangan": ""}])
        edit_i = st.data_editor(df_i, key=f"i_{st.session_state.key_i}", num_rows="dynamic", use_container_width=True)
        if st.button("Simpan ke BARANG_INDEN"):
            data = edit_i[edit_i["Part Number"] != ""]
            if not data.empty:
                sheet = get_sheet("BARANG_INDEN")
                if len(sheet.get_all_values()) == 0: sheet.append_row(["PART NUMBER", "DESKRIPSI", "QTY", "CUSTOMER", "KETERANGAN", "TANGGAL INPUT", "INISIAL", "DONE ORDER", "SAMPAI"])
                for _, r in data.iterrows():
                    sheet.append_row([r["Part Number"], r["Deskripsi"], r["QTY"], r["Customer"], r["Keterangan"], get_wita_time(), st.session_state.user, "FALSE", "FALSE"])
                st.cache_data.clear(); st.session_state.key_i += 1; st.rerun()

    # --- TAB 3: LAPORAN KOSONG ---
    with tab3:
        st.header("📦 Laporan Barang Kosong")
        try:
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
                            s = get_sheet("BARANG_KOSONG"); s.clear(); s.append_row(val[0]); s.append_rows(final_df.astype(str).values.tolist()); st.cache_data.clear(); st.rerun()
                st.subheader("✅ Done"); st.dataframe(d_df, use_container_width=True)
            else: st.info("Data Kosong belum tersedia.")
        except Exception as e: st.error(f"Error: {e}")

    # --- TAB 4: LAPORAN INDEN ---
    with tab4:
        st.header("🛒 Laporan Barang Inden")
        try:
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
                            s = get_sheet("BARANG_INDEN"); s.clear(); s.append_row(val[0]); s.append_rows(final_df.astype(str).values.tolist()); st.cache_data.clear(); st.rerun()
                st.subheader("✅ Done"); st.dataframe(d_df, use_container_width=True)
            else: st.info("Data Inden belum tersedia.")
        except Exception as e: st.error(f"Error: {e}")