import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Konfigurasi Halaman Web (Lebar penuh)
st.set_page_config(page_title="EWS Multi-Komoditas Terpadu", page_icon="🌿", layout="wide")

# ================= KODE CSS UNTUK MEMPERINDAH UI (BACKGROUND GAMBAR) =================
st.markdown("""
    <style>
    /* Mengubah Background Utama menjadi Gambar Pertanian dengan Efek Kaca Transparan */
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.75)), 
                          url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1920&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    /* Mempercantik font metrik angka agar terlihat melayang (Glassmorphism) */
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-left: 6px solid #2ecc71;
    }

    /* Mempercantik kotak analisis */
    .analisis-box {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Membuat latar menu tab sedikit berwarna agar jelas */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 10px 10px 0 0;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)
# =====================================================================================# =================================================================

@st.cache_data
def load_data():
    weather_df = pd.read_excel('EWS.xlsx', sheet_name='DATA CUACA')
    weather_df['Tanggal'] = pd.to_datetime(weather_df['Tanggal'])
    weather_df = weather_df.sort_values(by=['Provinsi', 'Tanggal']).reset_index(drop=True)
    weather_df['YearMonth'] = weather_df['Tanggal'].dt.to_period('M')

    enso_df = pd.read_excel('EWS.xlsx', sheet_name='ENSO INDEX')
    enso_col = [c for c in enso_df.columns if 'NINA34' in c][0]
    enso_df.rename(columns={enso_col: 'NINA34'}, inplace=True)
    enso_df['DATE'] = pd.to_datetime(enso_df['DATE'])
    enso_df['YearMonth'] = enso_df['DATE'].dt.to_period('M')

    df = pd.merge(weather_df, enso_df[['YearMonth', 'NINA34']], on='YearMonth', how='left')
    df.drop('YearMonth', axis=1, inplace=True)
    return df

df_mentah = load_data()

def proses_model_biologis(df_provinsi, komoditas, opt):
    pdf = df_provinsi.copy()
    pdf['Suhu_Rata2'] = (pdf['Tmax'] + pdf['Tmin']) / 2
    status_list, indikator_list, generasi_list = [], [], []
    
    # MESIN BIOLOGI (Logika Tetap Sama!)
    if opt == 'Ulat Kantong (Metisa plana)':
        t_base = 10; acc_gdd = 0; gen = 1
        for idx, row in pdf.iterrows():
            acc_gdd += max(row['Suhu_Rata2'] - t_base, 0)
            if acc_gdd > 380: acc_gdd -= 380; gen += 1
            indikator_list.append(acc_gdd); generasi_list.append(gen)
            if acc_gdd <= 62.8: status_list.append('Aman (Fase Telur)')
            elif acc_gdd <= 220: status_list.append('Bahaya (Instar Kritis)')
            else: status_list.append('Waspada (Pupa/Ngengat)')
        pdf['Satuan'] = '°C-day (GDD)'; pdf['Batas_1'] = 62.8; pdf['Batas_2'] = 220; pdf['Batas_Max'] = 380

    elif opt == 'Kumbang Tanduk (Oryctes rhinoceros)':
        t_base = 15; acc_gdd = 0; gen = 1
        for idx, row in pdf.iterrows():
            acc_gdd += max(row['Suhu_Rata2'] - t_base, 0)
            if acc_gdd > 1200: acc_gdd -= 1200; gen += 1
            indikator_list.append(acc_gdd); generasi_list.append(gen)
            if acc_gdd <= 300: status_list.append('Aman (Telur & Larva Awal)')
            elif acc_gdd <= 900: status_list.append('Waspada (Larva Lanjut/Pupa)')
            else: status_list.append('Bahaya (Imago Merusak Pucuk)')
        pdf['Satuan'] = '°C-day (GDD)'; pdf['Batas_1'] = 300; pdf['Batas_2'] = 900; pdf['Batas_Max'] = 1200
        
    elif opt == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
        pdf['Akumulasi_CH_7Hari'] = pdf['CH (mm)'].rolling(window=7, min_periods=1).sum()
        for ch in pdf['Akumulasi_CH_7Hari']:
            indikator_list.append(ch); generasi_list.append("-")
            if ch < 30: status_list.append('Aman (Kering - Spora Dormin)')
            elif ch <= 80: status_list.append('Waspada (Lembap - Spora Tumbuh)')
            else: status_list.append('Bahaya (Basah - Ledakan Infeksi)')
        pdf['Satuan'] = 'mm (Curah Hujan)'; pdf['Batas_1'] = 30; pdf['Batas_2'] = 80; pdf['Batas_Max'] = max(150, pdf['Akumulasi_CH_7Hari'].max())

    pdf['Nilai_Indikator'] = indikator_list
    pdf['Generasi'] = generasi_list
    pdf['Status_Hama'] = status_list
    return pdf

# MENU SAMPING
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3209/3209935.png", width=150)
st.sidebar.markdown("<h2 style='text-align: center; color: #2c3e50;'>Panel Kontrol</h2>", unsafe_allow_html=True)

prov_pilihan = st.sidebar.selectbox("📍 Pilih Provinsi:", sorted(df_mentah['Provinsi'].unique()))
st.sidebar.markdown("---")

komoditas = st.sidebar.selectbox("🌱 Pilih Komoditas:", ["Kelapa Sawit", "Karet", "Kelapa"])
if komoditas == "Kelapa Sawit": opt_pilihan = st.sidebar.selectbox("🐛 Pilih OPT:", ["Ulat Kantong (Metisa plana)"])
elif komoditas == "Kelapa": opt_pilihan = st.sidebar.selectbox("🐛 Pilih OPT:", ["Kumbang Tanduk (Oryctes rhinoceros)"])
else: opt_pilihan = st.sidebar.selectbox("🦠 Pilih OPT:", ["Penyakit Gugur Daun (Pestalotiopsis sp.)"])

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Rentang Waktu Analisis")
min_date, max_date = df_mentah['Tanggal'].min().date(), df_mentah['Tanggal'].max().date()
tanggal_pilihan = st.sidebar.date_input("Pilih Rentang Tanggal:", value=(min_date, max_date), min_value=min_date, max_value=max_date)

# PEMROSESAN DATA
df_terhitung = proses_model_biologis(df_mentah[df_mentah['Provinsi'] == prov_pilihan], komoditas, opt_pilihan)
if len(tanggal_pilihan) == 2:
    start_date, end_date = pd.to_datetime(tanggal_pilihan[0]), pd.to_datetime(tanggal_pilihan[1])
else:
    start_date, end_date = pd.to_datetime(min_date), pd.to_datetime(max_date)

filtered_df = df_terhitung[(df_terhitung['Tanggal'] >= start_date) & (df_terhitung['Tanggal'] <= end_date)].copy()

# TAMPILAN UTAMA
st.markdown(f"<h1 style='text-align: center; color: #2c3e50;'>🌱 Dashboard Intelijen Agronomi: {komoditas}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; font-size: 18px; color: #7f8c8d;'>📍 <b>Wilayah:</b> {prov_pilihan} | 🔍 <b>Fokus OPT:</b> {opt_pilihan}</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not filtered_df.empty:
    latest = filtered_df.iloc[-1]
    status_terkini, nino, nilai_ind = latest['Status_Hama'], latest['NINA34'], latest['Nilai_Indikator']
    
    if nino >= 0.5: status_enso, ikon_enso = "El Niño (Kering & Panas)", "🔥"
    elif nino <= -0.5: status_enso, ikon_enso = "La Niña (Basah & Dingin)", "🌧️"
    else: status_enso, ikon_enso = "Netral (Normal)", "⚖️"

    if "Aman" in status_terkini: bg_color, icon = 'linear-gradient(135deg, #2ecc71, #27ae60)', '✅'
    elif "Bahaya" in status_terkini: bg_color, icon = 'linear-gradient(135deg, #e74c3c, #c0392b)', '🚨'
    else: bg_color, icon = 'linear-gradient(135deg, #f1c40f, #f39c12)', '⚠️'

    # BARIS INDIKATOR UTAMA
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Indikator ({latest['Satuan']})", f"{nilai_ind:.1f}")
    col2.metric("Siklus / Generasi Ke-", f"{latest['Generasi']}")
    col3.metric("Indeks ENSO 3.4", f"{nino:.2f}", delta=status_enso, delta_color="off")
    
    st.markdown(f"""
        <div style="background: {bg_color}; padding: 25px; border-radius: 20px; text-align: center; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.1); margin-top: 10px; margin-bottom: 30px;">
            <h1 style="margin: 0; font-size: 38px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">{icon} {status_terkini.upper()}</h1>
            <p style="margin: 5px 0 0 0; font-size: 18px; opacity: 0.9;">Status Peringatan Dini Wilayah {prov_pilihan}</p>
        </div>
    """, unsafe_allow_html=True)

    # MEMBUAT TATA LETAK TAB (MENU NAVIGASI DALAM HALAMAN)
    tab1, tab2, tab3 = st.tabs(["📊 Kurva Risiko", "🧠 Analisis Pakar", "📋 Data Lapangan"])
    
    with tab1:
        st.markdown("<div class='analisis-box'>", unsafe_allow_html=True)
        st.markdown(f"### Dinamika Risiko {opt_pilihan}")
        fig = px.line(filtered_df, x='Tanggal', y='Nilai_Indikator', template='plotly_white')
        fig.add_hline(y=latest['Batas_1'], line_dash="dash", line_color="green", annotation_text="Batas Aman")
        fig.add_hline(y=latest['Batas_2'], line_dash="dash", line_color="red", annotation_text="Ambang Kritis")
        if latest['Batas_Max'] > latest['Batas_2']:
            fig.add_hline(y=latest['Batas_Max'], line_dash="solid", line_color="orange", annotation_text="Akhir Siklus")
        fig.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='analisis-box'>", unsafe_allow_html=True)
        st.markdown(f"#### 🌍 Dampak Iklim Makro {ikon_enso} terhadap **{prov_pilihan}**")
        if komoditas in ["Kelapa Sawit", "Kelapa"]:
            if nino >= 0.5: st.info(f"Anomali suhu **El Niño** memicu GDD agresif. Serangga merespons panas ekstrem ini dengan memperpendek siklus hidupnya. Waspadai ledakan populasi mendadak.")
            elif nino <= -0.5: st.info(f"**La Niña** membawa suhu sejuk. Penumpukan GDD melambat, memperpanjang umur larva. Curah hujan tinggi dapat mencuci hama dari tajuk daun.")
            else: st.info(f"Fase **Netral**. Siklus biologis berjalan normal sesuai kalender iklim.")
        else:
            if nino >= 0.5: st.info(f"Panasnya **El Niño** membuat spora jamur dorman. Risiko infeksi sangat rendah.")
            elif nino <= -0.5: st.error(f"🚨 **PERINGATAN LA NIÑA!** Hujan lebat menciptakan *micro-climate* basah, memicu penyebaran spora jamur mematikan secara sporadis.")
            else: st.info(f"Iklim **Netral**. Tetap waspada pada hari mendung berkepanjangan.")

        st.markdown("#### 🎯 Rekomendasi Tindakan Teknis")
        if opt_pilihan == 'Ulat Kantong (Metisa plana)':
            if "Aman" in status_terkini: st.success("Lakukan Sensus (1 pelepah per 5 pohon). Siapkan logistik insektisida biologi (B. thuringiensis).")
            elif "Bahaya" in status_terkini: st.error("TINDAKAN KILAT: Ulat merusak epidermis! Aplikasikan racun kontak (Deltametrin) / trunk injection sebelum kantong menebal.")
            else: st.warning("Hentikan penyemprotan udara (ulat kebal dalam kantong). Fokus kutip kepompong manual / lepas musuh alami (Sycanus).")
        elif opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            if "Aman" in status_terkini: st.success("Sanitasi kebun, cacah batang lapuk, dan tabur jamur Metarhizium anisopliae di tumpukan sampah organik.")
            elif "Waspada" in status_terkini: st.warning("Siapkan dan pasang perangkap feromon di batas blok kebun (rasio 1 perangkap per 2 Ha).")
            else: st.error("TINDAKAN KILAT: Kumbang aktif menggerek pucuk! Lakukan pengutipan manual dan tabur insektisida butiran (Karbofuran).")
        elif opt_pilihan == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
            if "Aman" in status_terkini: st.success("Risiko rendah. Lakukan pemupukan ekstra untuk menebalkan daun muda.")
            elif "Waspada" in status_terkini: st.warning("Semprotkan fungisida protektif (Mankozeb) secara preventif.")
            else: st.error("TINDAKAN KILAT: Lingkungan sangat basah. Gunakan fungisida sistemik (Heksakonazol) lewat *mist blower* / drone.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("<div class='analisis-box'>", unsafe_allow_html=True)
        st.markdown("### Transkrip Data Harian")
        kolom = ['Tanggal', 'CH (mm)', 'Suhu_Rata2', 'NINA34', 'Nilai_Indikator', 'Generasi', 'Status_Hama']
        tabel_tampil = filtered_df[kolom].copy()
        tabel_tampil['Tanggal'] = tabel_tampil['Tanggal'].dt.strftime('%d-%b-%Y')
        st.dataframe(tabel_tampil, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("Data tidak tersedia untuk rentang waktu/provinsi yang dipilih.")