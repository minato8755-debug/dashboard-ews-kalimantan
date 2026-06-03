import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="EWS Multi-Komoditas Terpadu", page_icon="🌿", layout="wide")

# ================= KODE CSS UNTUK MEMPERINDAH UI =================
st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
                          url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1920&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-left: 6px solid #2ecc71;
    }
    .analisis-box {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 10px 10px 0 0;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)
# =================================================================

# 2. Fungsi Memuat Data
@st.cache_data
def load_data():
    weather_df = pd.read_csv('EWS.xlsx - DATA CUACA.csv')
    weather_df['Tanggal'] = pd.to_datetime(weather_df['Tanggal'])
    weather_df = weather_df.sort_values(by=['Provinsi', 'Tanggal']).reset_index(drop=True)
    weather_df['YearMonth'] = weather_df['Tanggal'].dt.to_period('M')
    
    if 'RH' in weather_df.columns:
        weather_df.rename(columns={'RH': 'RH (%)'}, inplace=True)

    enso_df = pd.read_csv('EWS.xlsx - ENSO INDEX.csv')
    enso_col = [c for c in enso_df.columns if 'NINA34' in c][0]
    enso_df.rename(columns={enso_col: 'NINA34'}, inplace=True)
    enso_df['DATE'] = pd.to_datetime(enso_df['DATE'])
    enso_df['YearMonth'] = enso_df['DATE'].dt.to_period('M')

    df = pd.merge(weather_df, enso_df[['YearMonth', 'NINA34']], on='YearMonth', how='left')
    df.drop('YearMonth', axis=1, inplace=True)
    return df

df_mentah = load_data()

# 3. MESIN BIOLOGI BERDASARKAN LITERATUR SAINTIFIK TERBARU
def proses_model_biologis(df_provinsi, komoditas, opt):
    pdf = df_provinsi.copy()
    pdf['Suhu_Rata2'] = (pdf['Tmax'] + pdf['Tmin']) / 2
    status_list, indikator_list, generasi_list = [], [], []
    
    if opt == 'Ulat Kantong (Metisa plana)':
        t_base = 10.0 
        acc_gdd = 0; gen = 1
        for idx, row in pdf.iterrows():
            acc_gdd += max(row['Suhu_Rata2'] - t_base, 0)
            if acc_gdd > 2134: acc_gdd -= 2134; gen += 1 # Batas maksimal total siklus hidup
            indikator_list.append(acc_gdd); generasi_list.append(gen)
            
            if acc_gdd <= 200: status_list.append('Aman (Fase Telur & Awal Tetas)') # Telur & Pupa: 69-200 GDD
            elif acc_gdd <= 1283: status_list.append('Bahaya (Fase Larva Aktif Merusak)') # Larva butuh 555-1083 GDD
            else: status_list.append('Waspada (Pupa & Persiapan Dewasa)')
            
        pdf['Satuan'] = '°C-day (GDD)'; pdf['Batas_1'] = 200; pdf['Batas_2'] = 1283; pdf['Batas_Max'] = 2134

    elif opt == 'Kumbang Tanduk (Oryctes rhinoceros)':
        t_base = 11.5 
        acc_gdd = 0; gen = 1
        for idx, row in pdf.iterrows():
            acc_gdd += max(row['Suhu_Rata2'] - t_base, 0)
            if acc_gdd > 5000: acc_gdd -= 5000; gen += 1 # Siklus total (326-455 hari) ~ 5000 GDD
            indikator_list.append(acc_gdd); generasi_list.append(gen)
            
            if acc_gdd <= 230: status_list.append('Aman (Fase Telur di Kayu Lapuk)') # Telur 4-14 hari
            elif acc_gdd <= 4500: status_list.append('Waspada (Larva Instar 1-3 & Pupa)') # Larva 120-200 hari, Pupa 32-59 hari
            else: status_list.append('Bahaya (Imago/Kumbang Terbang Merusak)') 
            
        pdf['Satuan'] = '°C-day (GDD)'; pdf['Batas_1'] = 230; pdf['Batas_2'] = 4500; pdf['Batas_Max'] = 5000
        
    elif opt == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
        pdf['Akumulasi_CH_7Hari'] = pdf['CH (mm)'].rolling(window=7, min_periods=1).sum()
        pdf['Rata2_RH_7Hari'] = pdf['RH (%)'].rolling(window=7, min_periods=1).mean()
        
        for ch, rh in zip(pdf['Akumulasi_CH_7Hari'], pdf['Rata2_RH_7Hari']):
            indikator_list.append(ch); generasi_list.append("-")
            
            # Waspada = CH > 100mm/bulan (~25mm/minggu), Outbreak = CH > 300mm/bulan (~75mm/minggu)
            if ch < 25 or rh < 70:
                status_list.append('Aman (Udara Kering - Spora Mati)')
            elif 25 <= ch <= 75 and 70 <= rh <= 85:
                status_list.append('Waspada (Lembap - Spora Mulai Penetrasi)')
            elif ch > 75 and rh > 85:
                status_list.append('Bahaya (Sangat Basah - Wabah / Sporulasi Massal)')
            else:
                status_list.append('Waspada (Kondisi Iklim Mendukung)')
                
        pdf['Satuan'] = 'mm (Curah Hujan)'; pdf['Batas_1'] = 25; pdf['Batas_2'] = 75; pdf['Batas_Max'] = max(100, pdf['Akumulasi_CH_7Hari'].max())

    pdf['Nilai_Indikator'] = indikator_list
    pdf['Generasi'] = generasi_list
    pdf['Status_Hama'] = status_list
    return pdf

# 4. MENU SAMPING
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

# 5. TAMPILAN UTAMA
st.markdown(f"<h1 style='text-align: center; color: #2c3e50;'>🌱 Dashboard Intelijen Agronomi: {komoditas}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; font-size: 18px; color: #7f8c8d;'>📍 <b>Wilayah:</b> {prov_pilihan} | 🔍 <b>Fokus OPT:</b> {opt_pilihan}</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not filtered_df.empty:
    latest = filtered_df.iloc[-1]
    status_terkini, nino, nilai_ind = latest['Status_Hama'], latest['NINA34'], latest['Nilai_Indikator']
    rh_terkini = latest['RH (%)']
    
    if nino >= 0.5: status_enso, ikon_enso = "El Niño (Kering & Panas)", "🔥"
    elif nino <= -0.5: status_enso, ikon_enso = "La Niña (Basah & Dingin)", "🌧️"
    else: status_enso, ikon_enso = "Netral (Normal)", "⚖️"

    if "Aman" in status_terkini: bg_color, icon = 'linear-gradient(135deg, #2ecc71, #27ae60)', '✅'
    elif "Bahaya" in status_terkini: bg_color, icon = 'linear-gradient(135deg, #e74c3c, #c0392b)', '🚨'
    else: bg_color, icon = 'linear-gradient(135deg, #f1c40f, #f39c12)', '⚠️'

    # BARIS INDIKATOR UTAMA
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Indikator ({latest['Satuan']})", f"{nilai_ind:.1f}")
    col2.metric("Siklus Ke-", f"{latest['Generasi']}")
    col3.metric("Indeks ENSO 3.4", f"{nino:.2f}", delta=status_enso, delta_color="off")
    col4.metric("Kelembapan (RH)", f"{rh_terkini:.1f}%")
    
    st.markdown(f"""
        <div style="background: {bg_color}; padding: 25px; border-radius: 20px; text-align: center; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.1); margin-top: 10px; margin-bottom: 30px;">
            <h1 style="margin: 0; font-size: 38px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">{icon} {status_terkini.upper()}</h1>
            <p style="margin: 5px 0 0 0; font-size: 18px; opacity: 0.9;">Status Peringatan Dini Berbasis Jurnal Ilmiah</p>
        </div>
    """, unsafe_allow_html=True)

    # TATA LETAK TAB
    tab1, tab2, tab3 = st.tabs(["📊 Kurva Risiko", "🧠 Detail & Mitigasi Pakar (SOP)", "📋 Data Lapangan"])
    
    with tab1:
        st.markdown("<div class='analisis-box'>", unsafe_allow_html=True)
        st.markdown(f"### Dinamika Risiko {opt_pilihan}")
        fig = px.line(filtered_df, x='Tanggal', y='Nilai_Indikator', template='plotly_white')
        
        if opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            fig.add_hline(y=latest['Batas_1'], line_dash="dash", line_color="green", annotation_text="Akhir Telur (Aman)")
            fig.add_hline(y=latest['Batas_2'], line_dash="dash", line_color="orange", annotation_text="Larva Grub/Pupa (Waspada)")
            fig.add_hline(y=latest['Batas_Max'], line_dash="solid", line_color="red", annotation_text="Imago Terbang (Bahaya)")
        else:
            fig.add_hline(y=latest['Batas_1'], line_dash="dash", line_color="green", annotation_text="Batas Aman")
            fig.add_hline(y=latest['Batas_2'], line_dash="dash", line_color="red", annotation_text="Ambang Kritis")
            if latest['Batas_Max'] > latest['Batas_2']:
                fig.add_hline(y=latest['Batas_Max'], line_dash="solid", line_color="orange", annotation_text="Siklus Selesai")
                
        fig.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='analisis-box'>", unsafe_allow_html=True)
        st.markdown(f"#### 🧬 Karakteristik Biologi & Faktor Pemicu")
        
        if opt_pilihan == 'Ulat Kantong (Metisa plana)':
            st.info("""
            **Biologi Hama:** Spesies ini membutuhkan total akumulasi termal 1.440 °d - 2.134 °d. Fase Larva memakan porsi terlama (555 °d - 1.083 °d) dan merupakan fase pengrusakan tertinggi pada tajuk sawit. Fase Telur & Pupa lebih singkat (69 °d - 200 °d).
            """)
        elif opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            st.info("""
            **Siklus Panjang:** Satu generasi memakan waktu 326 hingga 455 hari! Larva (grub) memiliki 3 instar yang berlangsung 120-200 hari, sementara fase pra-pupa/pupa berlangsung 32-59 hari. Hama menghindari suhu di atas 37°C.  
            **Faktor Pemicu:** Metode *zero-burning* saat *replanting*. Batang sawit yang ditumbang/dicacah (*chipped trunks*) dan tumpukan Tandan Kosong Kelapa Sawit (TKKS) menjadi habitat pembiakan basah dan kaya nutrisi bagi hama.
            """)
        elif opt_pilihan == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
            st.info("""
            **Siklus Jamur 7-14 Hari:** *Pestalotiopsis sp.* merupakan patogen *airborne* & *waterborne*. Fase meliputi: **1. Inokulasi** (terbawa angin/air ke daun muda/flush); **2. Penetrasi** (12-24 jam masuk via stomata); **3. Nekrosis** (3-5 hari merusak sel daun); **4. Sporulasi** (7-14 hari menghasilkan *acervuli* bintik hitam pemicu spora baru).  
            **Faktor Iklim:** Kelembapan (RH) >85% + embun 8-10 jam mempercepat germinasi 3x lipat. RH di bawah 70% akan menghentikan penyebaran spora.
            """)

        st.markdown("#### 🛠️ Strategi Pengendalian Hama Terpadu (PHT/SOP)")
        if opt_pilihan == 'Ulat Kantong (Metisa plana)':
            if "Aman" in status_terkini: 
                st.success("**TINDAKAN (Fase Telur):** Lakukan Global Sensus (1 pelepah per 5 pohon). Persiapkan stok agen hayati *Bacillus thuringiensis* di gudang sebelum telur menetas serentak.")
            elif "Bahaya" in status_terkini: 
                st.error("**TINDAKAN KILAT (Fase Larva Aktif):** Ulat sedang rakus-rakusnya mengikis epidermis daun (Instar 1-3). Lakukan penyemprotan kontak atau injeksi batang (*trunk injection*) segera sebelum larva membuat kantong yang keras.")
            else: 
                st.warning("**TINDAKAN (Pupa):** Ulat memasuki masa kepompong dan bersiap menjadi ngengat. Semprotan pestisida tidak lagi berguna. Lakukan pengutipan kantong kepompong secara manual.")
        
        elif opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            if "Aman" in status_terkini: 
                st.success("**KULTUR TEKNIS (Fase Telur/Awal Larva):** Percepat penanaman Legume Cover Crop (*Mucuna bracteata*) pada area *replanting* untuk menutupi tumpukan cacahan batang sawit (menutup penciuman imago). Semprotkan jamur *Metarhizium anisopliae* pada tumpukan TKKS.")
            elif "Waspada" in status_terkini: 
                st.warning("**PENGENDALIAN HAYATI (Fase Pupa):** Larva grub telah membesar di dalam tanah/kayu. Pertimbangkan penyebaran agen hayati *Oryctes Nudivirus* (OrNV) yang sukses menginfeksi usus kumbang dan menurunkan daya bertelurnya.")
            else: 
                st.error("**TINDAKAN KILAT (Imago):** Kumbang dewasa merusak tajuk! Segera pasang **Ferotrap** (senyawa sintetik *ethyl 4-methyloctanoate*) dengan rasio 1 perangkap per 2 Hektar untuk menjebak imago terbang secara massal.")
        
        elif opt_pilihan == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
            if "Aman" in status_terkini: 
                st.success("**PREVENTIF (Spora Dorman):** Kelembapan di bawah 70% menghentikan sporulasi. Fokus lakukan sanitasi dan aplikasi *Trichoderma sp.* di atas tumpukan daun gugur agar tidak menjadi inokulum di musim hujan.")
            elif "Waspada" in status_terkini: 
                st.warning("**MITIGASI KIMIAWI (Curah Hujan Meningkat):** Waspada curah hujan mendekati 100 mm/bulan. Lakukan penyemprotan *mist blower* (*Propikonazol*, *Heksakonazol*, atau *Mankozeb*) terutama pada masa pembentukan daun muda (*flushing*).")
            else: 
                st.error("**TINDAKAN KILAT (Outbreak):** Curah hujan >300 mm/bulan & RH >85%. Rontok hebat sedang terjadi. **Kultur Teknis:** Segera injeksi pohon dengan pupuk ekstra Nitrogen (Urea 20-25%) dan Kalium (KCl) dari dosis normal untuk memaksa pohon memproduksi kanopi daun baru dengan cepat!")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("<div class='analisis-box'>", unsafe_allow_html=True)
        st.markdown("### Transkrip Data Harian Terpadu")
        kolom = ['Tanggal', 'CH (mm)', 'Tmax', 'Tmin', 'RH (%)', 'NINA34', 'Nilai_Indikator', 'Generasi', 'Status_Hama']
        tabel_tampil = filtered_df[kolom].copy()
        tabel_tampil['Tanggal'] = tabel_tampil['Tanggal'].dt.strftime('%d-%b-%Y')
        st.dataframe(tabel_tampil, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("Data tidak tersedia untuk rentang waktu/provinsi yang dipilih.")