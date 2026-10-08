📊 Auditoria de Telemetria: Geotab vs Vídeo Telemetria
Este repositório contém um conjunto de ferramentas em Python desenvolvidas para automatizar a extração de dados de telemetria veicular (Geotab) e realizar o cruzamento analítico com alertas de câmeras de vídeo telemetria (eventos de Start-Engine). O objetivo principal é auditar a eficiência dos equipamentos de vídeo, identificando falhas de gravação e alarmes falsos, além de plotar os resultados em mapas interativos.

🚀 Funcionalidades
Extração em Lote (API Geotab): Consulta múltiplas placas simultaneamente com sistema Anti-Queda (Retry automático) para contornar instabilidades de conexão ou bloqueios por excesso de requisições.

Mapeamento GPS Preciso: Busca coordenadas exatas de latitude e longitude consultando a entidade LogRecord no segundo exato em que a ignição foi acionada e desligada.

Cruzamento Espacial e Temporal: Pareamento automático de viagens da Geotab com os alertas da câmera usando uma janela de tolerância de 5 minutos.

Filtro de Ruídos (Guarda-chuva): Tratamento de alertas duplicados de Start-Engine dentro da mesma janela temporal, evitando penalizações injustas (falsos positivos).

Dashboard Interativo Web: Interface gráfica em Streamlit para upload de relatórios, visualização de métricas globais e por placa, download de planilhas tratadas e visualização em mapa interativo (Folium).

🛠️ Tecnologias Utilizadas
Linguagem: Python 3

Bibliotecas de Dados: pandas, openpyxl

APIs e Web: mygeotab, streamlit

Geolocalização: folium, streamlit-folium

📦 Instalação e Configuração
Clone este repositório para a sua máquina local:

Bash
git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
cd NOME_DO_REPOSITORIO
Instale as dependências necessárias através do pip:

Bash
pip install mygeotab pandas streamlit folium streamlit-folium openpyxl
⚙️ Como Utilizar
O projeto é dividido em dois scripts principais:

1. Extrator Geotab (extrator_geotab.py)
Script de linha de comando (CLI) responsável por puxar a rota histórica, inícios e fins de viagem direto da base da Geotab.

Como rodar: Execute python extrator_geotab.py no terminal.

Entradas: O script solicitará o nome da base, os SNs dos equipamentos (separados por vírgula) e o período de datas (DD/MM/AAAA).

Saída: Arquivo Excel (.xlsx) consolidado com todas as viagens e coordenadas.

2. Painel de Auditoria (app_auditoria.py)
Aplicação Web para cruzar o relatório gerado pela Geotab com o relatório bruto do portal de Vídeo Telemetria.

Como rodar: Execute python -m streamlit run app_auditoria.py no terminal.

Utilização: Faça o upload das duas planilhas na interface. O sistema calculará as seguintes métricas:

OK - Validado: Viagem confirmada por ambos os rastreadores.

FALHA - Sem Vídeo: Viagem maior que 5 minutos na Geotab sem registro da câmera.

FALHA - Geotab Ausente: Alarme gerado pela câmera sem nenhuma viagem real correspondente (Falso Alarme).

OK - Viagem Curta: Viagens com menos de 5 minutos (ignoradas no cálculo de penalização).

🧠 Regras de Negócio e Cálculo de Acertividade
A métrica de "Acertividade" do equipamento (calculada globalmente e por placa) segue a seguinte fórmula:

Plaintext
Acertividade = Viagens Validadas / (Viagens Validadas + Falhas Sem Vídeo + Falsos Alarmes)
Viagens curtas (< 5 minutos) são registradas no sistema, mas não entram no cálculo para não distorcer a nota do equipamento em manobras rápidas de pátio.