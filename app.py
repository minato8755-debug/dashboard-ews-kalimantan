import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="EWS Multi-Komoditas Terpadu", page_icon="🌾", layout="wide")

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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3209/3209935.png", width=100)
st.sidebar.title("Panel EWS Terpadu")

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
st.title(f"Dashboard Agroklimatologi: {komoditas}")
st.markdown(f"**Wilayah:** {prov_pilihan} | **Fokus OPT:** {opt_pilihan}")

if not filtered_df.empty:
    latest = filtered_df.iloc[-1]
    status_terkini, nino, nilai_ind = latest['Status_Hama'], latest['NINA34'], latest['Nilai_Indikator']
    
    # Deteksi ENSO
    if nino >= 0.5: status_enso, warna_enso, ikon_enso = "El Niño (Kering & Panas)", "#e67e22", "🔥"
    elif nino <= -0.5: status_enso, warna_enso, ikon_enso = "La Niña (Basah & Dingin)", "#2980b9", "🌧️"
    else: status_enso, warna_enso, ikon_enso = "Netral (Normal)", "#7f8c8d", "⚖️"

    # Deteksi Warna Status
    if "Aman" in status_terkini: bg_color, icon, alert_type = '#2ecc71', '✅', 'success'
    elif "Bahaya" in status_terkini: bg_color, icon, alert_type = '#e74c3c', '🚨', 'error'
    else: bg_color, icon, alert_type = '#f1c40f', '⚠️', 'warning'

    # METRIK ATAS
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Indikator Utama ({latest['Satuan']})", f"{nilai_ind:.1f}")
    col2.metric("Siklus / Generasi Ke-", f"{latest['Generasi']}")
    col3.metric("Indeks ENSO 3.4", f"{nino:.2f}", delta=status_enso, delta_color="off")
    
    st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 25px; border-radius: 12px; text-align: center; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 30px;">{icon} {status_terkini.upper()}</h1>
            <p style="margin: 5px 0 0 0; font-size: 16px;">Sistem Peringatan Dini {prov_pilihan}</p>
        </div>
    """, unsafe_allow_html=True)

    # ================= OTAL ANALISIS DINAMIS =================
    st.markdown("### 🧠 Analisis Sistem & Rekomendasi Tindakan")
    
    with st.container(border=True):
        st.markdown(f"#### 🌍 Dampak Iklim Makro {ikon_enso} terhadap Ekosistem **{prov_pilihan}**")
        
        # Logika silang antara Cuaca vs Jenis OPT
        if komoditas in ["Kelapa Sawit", "Kelapa"]: # Serangga (Butuh Panas)
            if nino >= 0.5:
                st.write(f"Indeks Niño3.4 berada di angka {nino:.2f}. Di wilayah {prov_pilihan}, anomali suhu **El Niño** memicu akumulasi GDD yang jauh lebih agresif. Serangga berdarah dingin ({opt_pilihan}) merespons panas ekstrem ini dengan **memperpendek siklus hidupnya**. Waspadai ledakan populasi (*outbreak*) karena generasi baru akan tumpang tindih dengan cepat.")
            elif nino <= -0.5:
                st.write(f"Indeks Niño3.4 menunjukkan **La Niña** ({nino:.2f}). Hujan ekstrem dan suhu sejuk di {prov_pilihan} sangat menguntungkan pekebun. Penumpukan GDD melambat, memperpanjang umur larva, dan tingginya intensitas hujan dapat secara alami mencuci hama kecil dari tajuk daun kelapa/sawit.")
            else:
                st.write(f"Kondisi iklim di {prov_pilihan} berada pada fase **Netral**. Siklus biologis serangga berjalan sesuai kalender agronomis normal.")
        else: # Jamur (Butuh Hujan)
            if nino >= 0.5:
                st.write(f"Anomali **El Niño** ({nino:.2f}) di {prov_pilihan} menciptakan udara panas dan kering. Ini adalah **kabar baik bagi kebun karet**. Spora *Pestalotiopsis sp.* menjadi dorman (tidak aktif) karena kurangnya kelembapan yang dibutuhkan untuk infeksi sekunder pada daun muda.")
            elif nino <= -0.5:
                st.write(f"🚨 **PERINGATAN LA NIÑA!** Indeks Niño3.4 berada di {nino:.2f}. Curah hujan lebat tiada henti di {prov_pilihan} menciptakan kondisi *micro-climate* tajuk yang sangat basah dan lembap. Ini adalah pemicu utama penyebaran spora jamur mematikan secara sporadis melalui cipratan air hujan.")
            else:
                st.write(f"Iklim **Netral** di {prov_pilihan}. Tetap waspada pada hari-hari pasca-hujan yang diikuti mendung berkepanjangan yang meningkatkan kelembapan tajuk.")

        st.markdown("#### 🎯 Rekomendasi Tindakan Teknis Lapangan")
        
        # Logika Rekomendasi berdasarkan Jenis Hama & Status
        if opt_pilihan == 'Ulat Kantong (Metisa plana)':
            if "Aman" in status_terkini:
                st.success("TINDAKAN: Lakukan Global Sensus (1 pelepah per 5 pohon). Titik fokus pengamatan adalah sisa-sisa generasi sebelumnya. Siapkan inventaris logistik insektisida biologi (Bacillus thuringiensis) di gudang sebelum fase kritis dimulai.")
            elif "Bahaya" in status_terkini:
                st.error("TINDAKAN KILAT: Larva sedang rakus-rakusnya merusak epidermis pelepah sawit! Segera aplikasikan racun kontak/lambung (seperti Deltametrin) atau *trunk injection* pada tanaman tinggi. Anda hanya memiliki waktu sempit sebelum mereka membungkus diri dengan kantong keras.")
            else:
                st.warning("TINDAKAN: Hentikan penyemprotan kimia udara, ulat sudah membentuk kepompong pelindung tebal sehingga penyemprotan hanya buang-buang biaya. Fokuskan tenaga kerja untuk pengutipan kepompong manual atau lepaskan musuh alami (predator *Sycanus*).")
                
        elif opt_pilihan == 'Kumbang Tanduk (Oryctes rhinoceros)':
            if "Aman" in status_terkini:
                st.success("TINDAKAN: Fase telur dan ulat gendon berada di bawah tanah atau di batang lapuk. Lakukan **sanitasi kebun**, cacah (chipping) batang kelapa/sawit tumbang, dan aplikasikan jamur *Metarhizium anisopliae* di tempat pembuangan sampah organik untuk membunuh ulat sejak dini.")
            elif "Waspada" in status_terkini:
                st.warning("TINDAKAN: Ulat gendon mulai menjadi pupa. Periksa kembali tumpukan tandan kosong (tankos) atau batang lapuk. Segera siapkan dan pasang perangkap feromon (Ferotrap) di batas-batas blok kebun dengan rasio 1 perangkap per 2 Hektar.")
            else:
                st.error("TINDAKAN KILAT: Kumbang dewasa (Imago) sedang aktif terbang dan menggerek titik tumbuh (pucuk/pupus) kelapa. Segera lakukan pengutipan kumbang manual dari tajuk, taburkan insektisida butiran (Karbofuran) di pucuk daun kelapa yang masih muda, dan periksa intensif pohon-pohon di pinggir jalan air.")
                
        elif opt_pilihan == 'Penyakit Gugur Daun (Pestalotiopsis sp.)':
            if "Aman" in status_terkini:
                st.success("TINDAKAN: Risiko infeksi sangat rendah. Lakukan pemupukan NPK ekstra untuk memastikan tanaman Karet memiliki energi yang cukup guna membentuk kanopi daun yang tebal dan sehat menjelang musim hujan depan.")
            elif "Waspada" in status_terkini:
                st.warning("TINDAKAN: Curah hujan mendukung perkecambahan spora. Lakukan pemantauan pada daun muda (fase flush). Jika kebun memiliki riwayat endemik, jadwalkan aplikasi fungisida protektif (seperti Mankozeb) dengan metode penyemprotan *mist blower* secara preventif.")
            else:
                st.error("TINDAKAN KILAT: Lingkungan basah sempurna bagi jamur! Gejala bercak daun cokelat menyebar cepat dan memicu gugur daun masal yang akan anjloknya produksi lateks. Segera gunakan **fungisida sistemik** (berbahan aktif Heksakonazol atau Propikonazol) menggunakan drone pertanian atau penyemprotan tajuk dosis tinggi. Hindari menyadap karet saat daun masih basah karena manusia bisa menjadi vektor penyebar spora!")

    st.divider()

    # GRAFIK INTERAKTIF
    st.markdown(f"### 📈 Dinamika Indikator ({latest['Satuan']})")
    fig = px.line(filtered_df, x='Tanggal', y='Nilai_Indikator', title=f"Kurva Risiko {opt_pilihan} di {prov_pilihan}")
    
    # Warna garis batas dinamis
    fig.add_hline(y=latest['Batas_1'], line_dash="dash", line_color="green", annotation_text="Batas Aman/Transisi")
    fig.add_hline(y=latest['Batas_2'], line_dash="dash", line_color="red", annotation_text="Ambang Kritis Lapangan")
    if latest['Batas_Max'] > latest['Batas_2']:
        fig.add_hline(y=latest['Batas_Max'], line_dash="solid", line_color="orange", annotation_text="Batas Akhir Siklus")
        
    st.plotly_chart(fig, use_container_width=True)

    # TABEL DATA
    st.markdown("### 📋 Transkrip Data Harian")
    kolom = ['Tanggal', 'CH (mm)', 'Suhu_Rata2', 'NINA34', 'Nilai_Indikator', 'Generasi', 'Status_Hama']
    tabel_tampil = filtered_df[kolom].copy()
    tabel_tampil['Tanggal'] = tabel_tampil['Tanggal'].dt.strftime('%d-%b-%Y')
    st.dataframe(tabel_tampil, use_container_width=True)
else:
    st.warning("Data tidak tersedia untuk rentang waktu/provinsi yang dipilih.")