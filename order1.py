import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI ---
SHEET_ID_ORDER = "1yRWMfWtA39Ookk-f8jptaUX86CUm4SRKOAVQ_2_af8o"
SCOPE = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

def get_sheet(tab_name):
    creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID_ORDER).worksheet(tab_name)

def main():
    # Session State
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

    st.sidebar.info(f"User Aktif: **{st.session_state.get('user', '')}**")
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
                if sheet.cell(1, 1).value is None: sheet.append_row(["PART NUMBER", "DESKRIPSI", "TANGGAL INPUT", "INISIAL", "DONE ORDER"])
                for _, r in data.iterrows():
                    sheet.append_row([r["Part Number"], r["Deskripsi"], datetime.now().strftime("%d-%m-%Y %H:%M"), st.session_state.user, "FALSE"])
                st.session_state.key_k += 1; st.rerun()

    # --- TAB 2: INPUT INDEN ---
    with tab2:
        st.header("Input Barang Inden")
        df_i = pd.DataFrame([{"Part Number": "", "Deskripsi": "", "QTY": 0, "Customer": "", "Keterangan": ""}])
        edit_i = st.data_editor(df_i, key=f"i_{st.session_state.key_i}", num_rows="dynamic", use_container_width=True)
        if st.button("Simpan ke BARANG_INDEN"):
            data = edit_i[edit_i["Part Number"] != ""]
            if not data.empty:
                sheet = get_sheet("BARANG_INDEN")
                if sheet.cell(1, 1).value is None: sheet.append_row(["PART NUMBER", "DESKRIPSI", "QTY", "CUSTOMER", "KETERANGAN", "TANGGAL INPUT", "INISIAL", "DONE ORDER", "SAMPAI"])
                for _, r in data.iterrows():
                    sheet.append_row([r["Part Number"], r["Deskripsi"], r["QTY"], r["Customer"], r["Keterangan"], datetime.now().strftime("%d-%m-%Y %H:%M"), st.session_state.user, "FALSE", "FALSE"])
                st.session_state.key_i += 1; st.rerun()

    # --- TAB 3: LAPORAN KOSONG ---
    with tab3:
        st.header("📦 Laporan Barang Kosong")
        try:
            s = get_sheet("BARANG_KOSONG"); val = s.get_all_values()
            df = pd.DataFrame(val[1:], columns=val[0])
            df["DONE ORDER"] = df["DONE ORDER"].str.upper() == 'TRUE'
            p_df = df[df["DONE ORDER"] == False].reset_index(drop=True); p_df.index += 1
            d_df = df[df["DONE ORDER"] == True].reset_index(drop=True); d_df.index += 1
            st.subheader("⏳ Pending"); st.dataframe(p_df, use_container_width=True)
            with st.expander("✏️ Update Status (Hanya Pending)"):
                with st.form("edit_k"):
                    edit_p = st.data_editor(p_df, column_config={"DONE ORDER": st.column_config.CheckboxColumn()})
                    if st.form_submit_button("Update"):
                        final_df = pd.concat([edit_p, d_df]); s.clear(); s.append_row(val[0]); s.append_rows(final_df.astype(str).values.tolist()); st.rerun()
            st.subheader("✅ Done"); st.dataframe(d_df, use_container_width=True)
        except: st.info("Data belum tersedia.")

    # --- TAB 4: LAPORAN INDEN ---
    with tab4:
        st.header("🛒 Laporan Barang Inden")
        try:
            s = get_sheet("BARANG_INDEN"); val = s.get_all_values()
            df = pd.DataFrame(val[1:], columns=val[0])
            df["DONE ORDER"] = df["DONE ORDER"].str.upper() == 'TRUE'
            df["SAMPAI"] = df["SAMPAI"].str.upper() == 'TRUE'
            mask = (df["DONE ORDER"] == False) | (df["SAMPAI"] == False)
            p_df = df[mask].reset_index(drop=True); p_df.index += 1
            d_df = df[~mask].reset_index(drop=True); d_df.index += 1
            st.subheader("⏳ Pending"); st.dataframe(p_df, use_container_width=True)
            with st.expander("✏️ Update Status (Hanya Pending)"):
                with st.form("edit_i"):
                    edit_p = st.data_editor(p_df, column_config={"DONE ORDER": st.column_config.CheckboxColumn(), "SAMPAI": st.column_config.CheckboxColumn()})
                    if st.form_submit_button("Update"):
                        final_df = pd.concat([edit_p, d_df]); s.clear(); s.append_row(val[0]); s.append_rows(final_df.astype(str).values.tolist()); st.rerun()
            st.subheader("✅ Done"); st.dataframe(d_df, use_container_width=True)
        except: st.info("Data belum tersedia.")