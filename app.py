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

# 2. Fungsi Memuat Data (SUDAH DIPERBAIKI: MEMBACA 1 FILE EXCEL 'EWS.xlsx')
@st.cache_data
def load_data():
    weather_df = pd.read_excel('EWS.xlsx', sheet_name='DATA CUACA')
    weather_df['Tanggal'] = pd.to_datetime(weather_df['Tanggal'])
    weather_df = weather_df.sort_values(by=['Provinsi', 'Tanggal']).reset_index(drop=True)
    weather_df['YearMonth'] = weather_df['Tanggal'].dt.to_period('M')
    
    if 'RH' in weather_df.columns:
        weather_df.rename(columns={'RH': 'RH (%)'}, inplace=True)

    enso_df = pd.read_excel('EWS.xlsx', sheet_name='ENSO INDEX')
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
            if acc_gdd > 2134: acc_gdd -= 2134; gen += 1 
            indikator_list.append(acc_gdd); generasi_list.append(gen)
            
            if acc_gdd <= 200: status_list.append('Aman (Fase Telur & Awal Tetas)')
            elif acc_gdd <= 1283: status_list.append('Bahaya (Fase Larva Aktif Merusak)')
            else: status_list.append('Waspada (Pupa & Persiapan Dewasa)')
            
        pdf['Satuan'] = '°C-day (GDD)'; pdf['Batas_1'] = 200; pdf['Batas_2'] = 1283; pdf['Batas_Max'] = 2134

    elif opt == 'Kumbang Tanduk (Oryctes rhinoceros)':
        t_base = 11.5 
        acc_gdd = 0; gen = 1
        for idx, row in pdf.iterrows():
            acc_gdd += max(row['Suhu_Rata2'] - t_base, 0)
            if acc_gdd > 5000: acc_gdd -= 5000; gen += 1 
            indikator_list.append(acc_gdd); generasi_list.append(gen)
            
            if acc_gdd <= 230: status_list.append('Aman (Fase Telur di Kayu Lapuk)')
            elif acc_gdd <= 4500: status_list.append('Waspada (Larva Instar 1-3 & Pupa)')
            else: status_list.append('Bahaya (Imago/Kumbang Terbang Merusak)') 
            
        pdf['Satuan'] = '°C-day (GDD)'; pdf['Batas_1'] = 230; pdf['Batas_2'] = 4500; pdf['Batas_Max'] = 5000
        
    elif opt == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
        pdf['Akumulasi_CH_7Hari'] = pdf['CH (mm)'].rolling(window=7, min_periods=1).sum()
        pdf['Rata2_RH_7Hari'] = pdf['RH (%)'].rolling(window=7, min_periods=1).mean()
        
        for ch, rh in zip(pdf['Akumulasi_CH_7Hari'], pdf['Rata2_RH_7Hari']):
            indikator_list.append(ch); generasi_list.append("-")
            
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
st.markdown(f"<h1 style='text-align: center; color: #2c3e50;'>🌱 Dashboard Agroklimatologi: {komoditas}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; font-size: 18px; color: #7f8c8d;'>📍 <b>Wilayah:</b> {prov_pilihan} | 🔍 <b>Fokus OPT:</b> {opt_pilihan}</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not filtered_df.empty:
    latest = filtered_df.iloc[-1]
    status_terkini, nino, nilai_ind = latest['Status_Hama'], latest['NINA34'], latest['Nilai_Indikator']
    rh_terkini = latest['RH (%)']
    
    if nino >= 0.5: status_enso, ikon_enso, iklim_teks = "El Niño (Kering & Panas)", "🔥", "El Niño"
    elif nino <= -0.5: status_enso, ikon_enso, iklim_teks = "La Niña (Basah & Dingin)", "🌧️", "La Niña"
    else: status_enso, ikon_enso, iklim_teks = "Netral (Normal)", "⚖️", "Netral"

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
    tab1, tab2, tab3 = st.tabs(["📊 Kurva Risiko", "🧠 Detail & Mitigasi", "📋 Data Lapangan"])
    
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
        st.markdown(f"#### 🧬 Karakteristik Biologi & Pengaruh Variabilitas ENSO ({ikon_enso} {iklim_teks})")
        
        if opt_pilihan == 'Ulat Kantong (Metisa plana)':
            st.info(f"""
            **Biologi Dasar:** Total akumulasi termal 1.440 °d - 2.134 °d. Fase Larva memakan porsi terlama (555 °d - 1.083 °d) dan merupakan fase pengrusakan tertinggi.
            
            **Korelasi ENSO ({iklim_teks}):** {"Kondisi panas El Niño membuat GDD terakumulasi secara agresif. Durasi instar larva menjadi jauh lebih singkat, sehingga ledakan (outbreak) terjadi sangat mendadak. Udara kering menekan agen hayati alami, memperburuk kerusakan." if nino >= 0.5 else "Kondisi basah La Niña memperlambat GDD. Siklus hidup ulat memanjang, namun curah hujan dan kelembapan yang tinggi sangat menguntungkan penyebaran jamur entomopatogen alami yang dapat membunuh larva di lapangan." if nino <= -0.5 else "Kondisi iklim Netral. Akumulasi GDD dan siklus hidup hama berjalan sesuai kalender agronomis normal tanpa anomali kecepatan tetas."}
            """)
            
        elif opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            st.info(f"""
            **Biologi Dasar:** Siklus sangat panjang (326-455 hari). Fase larva/grub di kayu lapuk berlangsung 120-200 hari. Metode *zero-burning* dan tumpukan TKKS adalah pemicu utamanya.
            
            **Korelasi ENSO ({iklim_teks}):** {"Kekeringan akibat El Niño membuat tumpukan bahan organik (breeding site) cepat kering. Meski menghambat larva, suhu ekstrem memaksa imago/kumbang dewasa terbang lebih agresif mencari sumber air dan makanan di tajuk/pucuk sawit muda." if nino >= 0.5 else "La Niña memicu pelapukan kayu dan TKKS lebih cepat akibat terendam air. Hal ini menciptakan sarang larva (grub) yang sangat melimpah. Namun, kelembapan ini juga memfasilitasi epidemi jamur *Metarhizium* secara masif." if nino <= -0.5 else "Iklim Netral. Degradasi *breeding site* (batang lapuk) berjalan perlahan, populasi larva stabil di bawah tanah."}
            """)
            
        elif opt_pilihan == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
            st.info(f"""
            **Biologi Dasar:** Patogen *airborne* & *waterborne*. Siklus 7-14 hari. RH >85% + embun 8-10 jam mempercepat germinasi spora 3x lipat. 
            
            **Korelasi ENSO ({iklim_teks}):** {"El Niño menekan curah hujan dan RH tajuk turun secara drastis. Ini adalah KONDISI TERBAIK bagi pekebun karena lingkungan udara kering secara paksa menggagalkan proses penetrasi spora ke dalam stomata." if nino >= 0.5 else "La Niña adalah ANCAMAN UTAMA untuk patogen ini. Hujan deras >300mm/bulan disertai mendung tebal menjaga RH absolut di atas 85%. Kondisi ini memicu pelepasan *acervuli* secara beruntun dan *outbreak* gugur daun masif tidak dapat dihindari tanpa intervensi kimia." if nino <= -0.5 else "Iklim Netral dengan kelembapan transisi. Infeksi spora berjalan sporadis tergantung embun pagi dan hujan lokal."}
            """)

        st.markdown(f"#### 🛠️ Strategi Mitigasi Terpadu Berbasis Fase & Iklim ({iklim_teks})")
        
        if opt_pilihan == 'Ulat Kantong (Metisa plana)':
            if "Aman" in status_terkini: 
                mitigasi = "Lakukan sensus (1 pelepah/5 pohon)."
                if nino >= 0.5: mitigasi += " **Tindakan Khusus El Niño:** Karena panas ekstrem mempercepat penetasan, interval sensus harus dirapatkan menjadi seminggu sekali. Siapkan B. thuringiensis lebih awal."
                st.success(f"**FASE TELUR:** {mitigasi}")
            elif "Bahaya" in status_terkini: 
                mitigasi = "Larva (Instar 1-3) sangat rakus. Lakukan penyemprotan insektisida kontak/injeksi batang segera."
                if nino <= -0.5: mitigasi += " **Tindakan Khusus La Niña:** Hujan akan mencuci insektisida semprot. Prioritaskan *trunk injection* (injeksi batang) agar racun sistemik sampai ke daun tanpa hilang tercuci hujan."
                st.error(f"**FASE LARVA AKTIF:** {mitigasi}")
            else: 
                st.warning("**FASE PUPA:** Ulat di dalam kepompong tebal. Pestisida tidak efektif. Lakukan pengutipan kantong secara manual dan pastikan *breeding site* bersih.")
                
        elif opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            if "Aman" in status_terkini: 
                mitigasi = "Tanam kacangan (*Mucuna bracteata*) untuk menutup tumpukan kayu lapuk."
                if nino <= -0.5: mitigasi += " **Tindakan Khusus La Niña:** Kayu basah sangat disukai larva. Manfaatkan momen basah ini dengan menabur jamur *Metarhizium anisopliae* di tumpukan TKKS, karena jamur akan menyebar pesat."
                st.success(f"**FASE TELUR & LARVA:** {mitigasi}")
            elif "Waspada" in status_terkini: 
                st.warning("**FASE PUPA:** Larva membesar di kayu. Sebarkan agen hayati *Oryctes Nudivirus* (OrNV) di lapangan untuk menurunkan fekunditas (daya tetas) kumbang.")
            else: 
                mitigasi = "Imago merusak pucuk! Pasang **Ferotrap** (1 trap/2 Ha)."
                if nino >= 0.5: mitigasi += " **Tindakan Khusus El Niño:** Kumbang haus air dan akan menyerang pucuk muda (umbut) secara brutal. Tambahkan aplikasi insektisida butiran (*Karbofuran*) langsung pada pucuk kelapa muda."
                st.error(f"**FASE IMAGO/DEWASA:** {mitigasi}")
                
        elif opt_pilihan == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
            if "Aman" in status_terkini: 
                mitigasi = "Fokus pada sanitasi sisa daun di tanah."
                if nino >= 0.5: mitigasi += " **Tindakan Khusus El Niño:** Cuaca kering adalah waktu emas! Genjot pemupukan Nitrogen (Urea 20-25%) dan Kalium (KCl) untuk memacu pembentukan daun baru (*flush*) setebal mungkin sebelum musim hujan tiba."
                st.success(f"**SPORA DORMAN:** {mitigasi}")
            elif "Waspada" in status_terkini: 
                st.warning("**PRA-INFEKSI:** Hujan dan RH meningkat. Aplikasikan fungisida protektif (*Mankozeb 80 WP*) dengan *mist-blower* pada daun muda untuk mencegah spora menembus stomata.")
            else: 
                mitigasi = "Wabah sedang terjadi! Daun mulai rontok masif."
                if nino <= -0.5: mitigasi += " **Tindakan Khusus La Niña:** Kelembapan absolut memicu infeksi harian. Segera lakukan pengasapan (*fogging*) fungisida Triazol (*Propikonazol/Heksakonazol*). Taburkan jamur *Trichoderma sp.* di tanah untuk menghancurkan daun rontok yang terinfeksi."
                st.error(f"**OUTBREAK (LEDANG JAMUR):** {mitigasi}")
                
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