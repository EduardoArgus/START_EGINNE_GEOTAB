import streamlit as st
import pandas as pd
from datetime import timedelta
import folium
from streamlit_folium import st_folium
import io

st.set_page_config(page_title="Auditoria de Telemetria", layout="wide")

st.title("Auditoria Espacial: Geotab vs Vídeo Telemetria")
st.markdown("Faça o upload dos relatórios exportados para cruzar os eventos de **Início de Viagem (Geotab)** e **Start-Engine (Vídeo)**.")

col1, col2 = st.columns(2)
with col1:
    arq_geotab = st.file_uploader("Upload Relatório Geotab (Excel)", type=["xlsx", "xls"])
with col2:
    arq_video = st.file_uploader("Upload Relatório Vídeo Telemetria (Excel)", type=["xlsx", "xls"])

if arq_geotab and arq_video:
    if st.button("Iniciar Cruzamento de Dados", type="primary"):
        with st.spinner("Processando e cruzando dados..."):
            try:
                # 1. Carregar Geotab
                df_geotab = pd.read_excel(arq_geotab)
                df_geotab['Inicio_Viagem'] = pd.to_datetime(df_geotab['Inicio_Viagem'])
                df_geotab['Duracao_TimeDelta'] = pd.to_timedelta(df_geotab['Tempo_Direcao'].astype(str))
                
                # 2. Carregar Vídeo Telemetria
                df_video = pd.read_excel(arq_video, header=3)
                df_video['Alarm Time'] = pd.to_datetime(df_video['Alarm Time'])
                df_video = df_video[df_video['Alarm Type'] == 'Start-Engine'].copy()
                
                # --- NOVO: Remoção de Duplicatas da Vídeo Telemetria ---
                df_video = df_video.drop_duplicates(
                    subset=['Plate Number', 'Alarm Time', 'Latitude', 'Longitude']
                ).reset_index(drop=True)
                # -------------------------------------------------------
                
                # 3. Cruzamento Geotab -> Vídeo
                resultados = []
                video_eventos_usados = set()
                
                for idx, trip in df_geotab.iterrows():
                    inicio_geo = trip['Inicio_Viagem']
                    lat_geo = trip['Lat_Inicio']
                    lon_geo = trip['Long_Inicio']
                    duracao = trip['Duracao_TimeDelta']
                    placa_geotab = str(trip['SN']).strip()
                    
                    limite_inferior = inicio_geo - timedelta(minutes=5)
                    limite_superior = inicio_geo + timedelta(minutes=5)
                    
                    # Filtra eventos de vídeo na janela de 5 minutos E da mesma placa
                    eventos_validos = df_video[
                        (df_video['Alarm Time'] >= limite_inferior) & 
                        (df_video['Alarm Time'] <= limite_superior) &
                        (df_video['Plate Number'].astype(str).str.strip() == placa_geotab)
                    ]
                    
                    if not eventos_validos.empty:
                        evento_proximo = eventos_validos.iloc[(eventos_validos['Alarm Time'] - inicio_geo).abs().argsort()[:1]]
                        
                        # NOVA REGRA: Adiciona TODOS os eventos encontrados nessa janela de 5 min como "usados",
                        # evitando que os alertas duplicados/seguidos virem falsos alarmes depois.
                        video_eventos_usados.update(eventos_validos.index.tolist())
                        
                        video_time = evento_proximo['Alarm Time'].values[0]
                        video_lat = evento_proximo['Latitude'].values[0]
                        video_lon = evento_proximo['Longitude'].values[0]
                        status = "OK - Validado"
                    else:
                        video_time, video_lat, video_lon = None, None, None
                        
                        if pd.notna(duracao) and duracao > timedelta(minutes=5):
                            status = "FALHA - Sem Vídeo"
                        else:
                            status = "OK - Viagem Curta (< 5 min)"
                            
                    resultados.append({
                        'Placa/SN': trip['SN'],
                        'Inicio_Geotab': inicio_geo,
                        'Duracao_Viagem': trip['Tempo_Direcao'],
                        'Video_Start_Time': video_time,
                        'Status_Auditoria': status,
                        'Lat_Geotab': lat_geo,
                        'Lon_Geotab': lon_geo,
                        'Lat_Video': video_lat,
                        'Lon_Video': video_lon
                    })
                    
                # 4. Cruzamento Reverso (Falsos Alarmes de Vídeo)
                for idx_vid, row_vid in df_video.iterrows():
                    if idx_vid not in video_eventos_usados:
                        resultados.append({
                            'Placa/SN': str(row_vid.get('Plate Number', 'Desconhecido')).strip(),
                            'Inicio_Geotab': pd.NaT,
                            'Duracao_Viagem': '00:00:00',
                            'Video_Start_Time': row_vid['Alarm Time'],
                            'Status_Auditoria': 'FALHA - Geotab Ausente',
                            'Lat_Geotab': None,
                            'Lon_Geotab': None,
                            'Lat_Video': row_vid.get('Latitude'),
                            'Lon_Video': row_vid.get('Longitude')
                        })
                    
                df_resultado = pd.DataFrame(resultados)
                
                # ================= Indicadores Globais =================
                qtd_ok = len(df_resultado[df_resultado['Status_Auditoria'] == 'OK - Validado'])
                qtd_falha_video = len(df_resultado[df_resultado['Status_Auditoria'] == 'FALHA - Sem Vídeo'])
                qtd_falha_geotab = len(df_resultado[df_resultado['Status_Auditoria'] == 'FALHA - Geotab Ausente'])
                qtd_ignorada = len(df_resultado[df_resultado['Status_Auditoria'] == 'OK - Viagem Curta (< 5 min)'])
                
                total_auditado = qtd_ok + qtd_falha_video + qtd_falha_geotab
                acertividade_global = (qtd_ok / total_auditado) * 100 if total_auditado > 0 else 0.0
                
                st.divider()
                st.subheader("Métricas Globais de Desempenho")
                colA, colB, colC, colD = st.columns(4)
                colA.metric("Validadas (Com Vídeo)", qtd_ok)
                colB.metric("Falha de Câmera (Sem Vídeo)", qtd_falha_video)
                colC.metric("Falha de Geotab (Falso Alarme)", qtd_falha_geotab)
                colD.metric("Taxa de Acerto Geral", f"{acertividade_global:.1f}%")
                st.caption(f"Viagens Curtas ignoradas no cálculo: {qtd_ignorada}")
                
                # ================= Acertividade por Placa =================
                st.divider()
                st.subheader("Acertividade por Placa / Equipamento")
                
                def calcular_metricas_placa(grupo):
                    validadas = (grupo['Status_Auditoria'] == 'OK - Validado').sum()
                    falha_video = (grupo['Status_Auditoria'] == 'FALHA - Sem Vídeo').sum()
                    falso_alarme = (grupo['Status_Auditoria'] == 'FALHA - Geotab Ausente').sum()
                    ignoradas = (grupo['Status_Auditoria'] == 'OK - Viagem Curta (< 5 min)').sum()
                    
                    total = validadas + falha_video + falso_alarme
                    taxa = (validadas / total) * 100 if total > 0 else 0.0
                    
                    return pd.Series({
                        'Viagens Validadas': validadas,
                        'Falhas (Sem Vídeo)': falha_video,
                        'Falsos Alarmes(Sem Geotab)': falso_alarme,
                        'Viagens Curtas': ignoradas,
                        'Acertividade': f"{taxa:.1f}%"
                    })
                
                resumo_placas = df_resultado.groupby('Placa/SN').apply(calcular_metricas_placa).reset_index()
                st.dataframe(resumo_placas, use_container_width=True)

                # ================= Formatação da Tabela Detalhada =================
                st.divider()
                st.subheader("Tabela de Detalhamento de Viagens")
                
                df_display = df_resultado.copy()
                df_display['Inicio_Geotab'] = df_display['Inicio_Geotab'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('-')
                df_display['Video_Start_Time'] = pd.to_datetime(df_display['Video_Start_Time']).dt.strftime('%d/%m/%Y %H:%M:%S').fillna('-')
                
                st.dataframe(df_display, use_container_width=True)
                
                # Exportação
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    resumo_placas.to_excel(writer, index=False, sheet_name='Resumo_Por_Placa')
                    df_display.to_excel(writer, index=False, sheet_name='Detalhamento_Viagens')
                
                st.download_button(
                    label="📥 Baixar Relatório Completo (Excel)",
                    data=buffer.getvalue(),
                    file_name="Auditoria_StartEngine_Completa.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # ================= Mapeamento =================
                st.divider()
                st.subheader("Visualização Espacial das Inicializações")
                
                lat_centro = df_resultado['Lat_Geotab'].dropna().iloc[0] if not df_resultado['Lat_Geotab'].dropna().empty else df_resultado['Lat_Video'].dropna().iloc[0]
                lon_centro = df_resultado['Lon_Geotab'].dropna().iloc[0] if not df_resultado['Lon_Geotab'].dropna().empty else df_resultado['Lon_Video'].dropna().iloc[0]
                
                mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=11)
                
                for _, row in df_resultado.iterrows():
                    placa = row['Placa/SN']
                    
                    if pd.notna(row['Lat_Geotab']) and pd.notna(row['Lon_Geotab']):
                        loc_geotab = [row['Lat_Geotab'], row['Lon_Geotab']]
                        inicio_fmt = row['Inicio_Geotab'].strftime('%d/%m/%Y %H:%M:%S') if pd.notna(row['Inicio_Geotab']) else "N/A"
                        info_geo = f"<b>{placa} (Geotab)</b><br>Início: {inicio_fmt}<br>Duração: {row['Duracao_Viagem']}"
                        
                        if row['Status_Auditoria'] == 'FALHA - Sem Vídeo':
                            folium.Marker(
                                location=loc_geotab,
                                popup=folium.Popup(info_geo + "<br><b style='color:red;'>FALHA: Vídeo ausente</b>", max_width=300),
                                icon=folium.Icon(color='red', icon='info-sign')
                            ).add_to(mapa)
                            
                        elif row['Status_Auditoria'] == 'OK - Validado':
                            folium.Marker(
                                location=loc_geotab,
                                popup=folium.Popup(info_geo, max_width=300),
                                icon=folium.Icon(color='blue', icon='play')
                            ).add_to(mapa)
                            
                            if pd.notna(row['Lat_Video']) and pd.notna(row['Lon_Video']):
                                loc_video = [row['Lat_Video'], row['Lon_Video']]
                                video_fmt = pd.to_datetime(row['Video_Start_Time']).strftime('%d/%m/%Y %H:%M:%S')
                                folium.Marker(
                                    location=loc_video,
                                    popup=folium.Popup(f"<b>{placa} (Vídeo)</b><br>Alarme: {video_fmt}", max_width=300),
                                    icon=folium.Icon(color='green', icon='camera')
                                ).add_to(mapa)
                                folium.PolyLine([loc_geotab, loc_video], color="gray", weight=2, dash_array='5').add_to(mapa)

                        elif row['Status_Auditoria'] == 'OK - Viagem Curta (< 5 min)':
                            folium.Marker(
                                location=loc_geotab,
                                popup=folium.Popup(info_geo + "<br>Viagem Curta (Ignorada)", max_width=300),
                                icon=folium.Icon(color='lightgray', icon='minus')
                            ).add_to(mapa)

                    elif row['Status_Auditoria'] == 'FALHA - Geotab Ausente':
                        if pd.notna(row['Lat_Video']) and pd.notna(row['Lon_Video']):
                            loc_video = [row['Lat_Video'], row['Lon_Video']]
                            video_fmt = pd.to_datetime(row['Video_Start_Time']).strftime('%d/%m/%Y %H:%M:%S')
                            folium.Marker(
                                location=loc_video,
                                popup=folium.Popup(f"<b style='color:orange;'>Falso Alarme (Sem Geotab)({placa})</b><br>Data/Hora: {video_fmt}", max_width=300),
                                icon=folium.Icon(color='orange', icon='warning-sign')
                            ).add_to(mapa)
                        
                st_folium(mapa, width=1200, height=600, returned_objects=[])

            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento: {e}")