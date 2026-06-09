import streamlit as st
import app1
import order1

st.set_page_config(page_title="Sistem Terpadu", layout="wide")

st.sidebar.title("Menu Navigasi")
pilih = st.sidebar.radio("Pilih Modul:", ["📦 Quotation Database", "📝 Orderbook System"])

if pilih == "📦 Quotation Database":
    app1.main()
else:
    order1.main()