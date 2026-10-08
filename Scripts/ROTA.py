import mygeotab
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

# ================= Credenciais Fixas =================
USERNAME = 'X'
PASSWORD = 'X'
SERVER = 'my.geotab.com'  

# ================= Entradas pelo Terminal =================
print("--- Extrator de Viagens Geotab (Múltiplos Equipamentos - Anti-Queda) ---")
DATABASE = input("Digite o nome da base (database): ").strip()
ENTRADA_SNS = input("Digite os SNs dos equipamentos (separados por vírgula): ").strip()
DATA_INICIO_STR = input("Digite a data INICIAL (formato DD/MM/AAAA): ").strip()
DATA_FIM_STR = input("Digite a data FINAL (formato DD/MM/AAAA): ").strip()

lista_sns = [sn.strip() for sn in ENTRADA_SNS.split(',') if sn.strip()]

if not lista_sns:
    print("Nenhum SN válido informado.")
    sys.exit()

try:
    start_date = datetime.strptime(DATA_INICIO_STR, '%d/%m/%Y')
    end_date_input = datetime.strptime(DATA_FIM_STR, '%d/%m/%Y')
    if end_date_input < start_date:
        print("Erro: A data final não pode ser menor que a data inicial.")
        sys.exit()
except ValueError:
    print("Formato de data inválido. Por favor, use o formato DD/MM/AAAA.")
    sys.exit()

# ================= Autenticação =================
print(f"\nAutenticando na base '{DATABASE}'...")
try:
    api = mygeotab.API(username=USERNAME, password=PASSWORD, database=DATABASE, server=SERVER)
    api.authenticate()
    print("Autenticação bem-sucedida!\n")
except Exception as e:
    print(f"Erro na autenticação: {e}")
    sys.exit()

# ================= Função Anti-Queda (Retry) =================
def buscar_com_tentativas(entidade, search, limite=None, max_tentativas=5, espera=3):
    """Tenta fazer a requisição na API. Se cair, espera alguns segundos e tenta de novo."""
    for tentativa in range(max_tentativas):
        try:
            if limite:
                return api.get(entidade, search=search, resultsLimit=limite)
            else:
                return api.get(entidade, search=search)
        except Exception as e:
            print(f"      [Aviso] Conexão instável ao buscar {entidade}. Tentativa {tentativa + 1} de {max_tentativas}. Aguardando {espera}s...")
            time.sleep(espera)
            # Reconectar caso a sessão tenha sido derrubada completamente
            try:
                api.authenticate()
            except:
                pass
            espera += 2 # Aumenta o tempo de espera a cada falha
    
    print(f"      [Erro] Falha definitiva ao buscar {entidade} após {max_tentativas} tentativas.")
    return None

# ================= Lógica de Busca =================
def buscar_multiplas_viagens(sns, start_date, end_date_input):
    end_date = end_date_input + timedelta(days=1)
    dados_viagens = []
    
    for sn in sns:
        print(f"Buscando o dispositivo SN: {sn}...")
        devices = buscar_com_tentativas('Device', search={'serialNumber': sn})
        
        if not devices:
            print(f" > Equipamento com SN {sn} não encontrado ou erro de conexão. Pulando...\n")
            continue
            
        device_id = devices[0]['id']
        device_name = devices[0].get('name', 'Sem Nome')
        print(f" > Dispositivo encontrado: {device_name}. Extraindo viagens...")
        
        trips = buscar_com_tentativas('Trip', search={
            'deviceSearch': {'id': device_id},
            'fromDate': start_date,
            'toDate': end_date
        })
        
        if not trips:
            print(f" > Nenhuma viagem encontrada para {device_name} neste período.\n")
            continue
            
        print(f" > {len(trips)} viagens encontradas. Coletando coordenadas (com proteção de conexão)...")
        
        for trip in trips:
            inicio_utc = trip.get('start')
            fim_utc = trip.get('stop')
            
            lat_inicio, lon_inicio = None, None
            lat_fim, lon_fim = None, None
            
            if inicio_utc:
                log_inicio = buscar_com_tentativas('LogRecord', search={'deviceSearch': {'id': device_id}, 'fromDate': inicio_utc}, limite=1)
                if log_inicio:
                    lat_inicio = log_inicio[0].get('latitude')
                    lon_inicio = log_inicio[0].get('longitude')
                    
            if fim_utc:
                log_fim = buscar_com_tentativas('LogRecord', search={'deviceSearch': {'id': device_id}, 'fromDate': fim_utc}, limite=1)
                if log_fim:
                    lat_fim = log_fim[0].get('latitude')
                    lon_fim = log_fim[0].get('longitude')

            inicio_local = (inicio_utc - timedelta(hours=3)).replace(tzinfo=None) if inicio_utc else None
            fim_local = (fim_utc - timedelta(hours=3)).replace(tzinfo=None) if fim_utc else None
            duracao = str(trip.get('drivingDuration')).split('.')[0] if trip.get('drivingDuration') else '00:00:00'
            
            dados_viagens.append({
                'Veiculo': device_name,
                'SN': sn,
                'Inicio_Viagem': inicio_local,
                'Fim_Viagem': fim_local,
                'Tempo_Direcao': duracao,
                'Distancia_km': round(trip.get('distance', 0), 2),
                'Velocidade_Maxima_kmh': round(trip.get('maximumSpeed', 0), 2),
                'Lat_Inicio': lat_inicio,
                'Long_Inicio': lon_inicio,
                'Lat_Fim': lat_fim,
                'Long_Fim': lon_fim
            })
            
            # Pequena pausa de 0.1s entre as viagens para não sobrecarregar o servidor
            time.sleep(0.1)
            
        print(" > Concluído.\n")
        
    if not dados_viagens:
        return pd.DataFrame()
        
    df_trips = pd.DataFrame(dados_viagens)
    df_trips = df_trips.sort_values(by=['Veiculo', 'Inicio_Viagem']).reset_index(drop=True)
    
    return df_trips

# ================= Execução e Exportação =================
df_historico = buscar_multiplas_viagens(lista_sns, start_date, end_date_input)

if df_historico is not None and not df_historico.empty:
    data_ini = start_date.strftime('%d-%m-%Y')
    data_fim = end_date_input.strftime('%d-%m-%Y')
    
    if len(lista_sns) == 1:
        nome_arquivo = f"Viagens_{lista_sns[0]}_{data_ini}_a_{data_fim}.xlsx" if data_ini != data_fim else f"Viagens_{lista_sns[0]}_{data_ini}.xlsx"
    else:
        nome_arquivo = f"Viagens_Multiplos_{len(lista_sns)}_Veiculos_{data_ini}_a_{data_fim}.xlsx" if data_ini != data_fim else f"Viagens_Multiplos_{len(lista_sns)}_Veiculos_{data_ini}.xlsx"
    
    try:
        df_historico.to_excel(nome_arquivo, index=False, engine='openpyxl')
        print(f"Sucesso! {len(df_historico)} viagens exportadas de {len(lista_sns)} equipamento(s).")
        print(f"O arquivo '{nome_arquivo}' foi salvo na mesma pasta do script.")
    except Exception as e:
        print(f"\nErro ao salvar o arquivo Excel: {e}")
else:
    print("Não foram gerados dados para exportação.")