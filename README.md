O projeto é um sistema construído para auditar a confiabilidade das câmeras de vídeo telemetria da frota, utilizando os dados de GPS da Geotab como prova real.

Ele é dividido em duas ferramentas principais:

Extrator de Dados (Geotab): Um script que se conecta à base da Geotab e puxa automaticamente todo o histórico de viagens (com latitude e longitude exatas) de múltiplos veículos de uma só vez. Ele possui um sistema "anti-queda" que tenta reconectar sozinho caso o servidor derrube a conexão.

Painel de Auditoria (Web): Uma interface interativa onde você faz o upload da planilha da Geotab e da planilha da câmera. O sistema cruza os dados e classifica cada evento:

Validado: O veículo ligou (Geotab) e a câmera registrou (Vídeo) no mesmo intervalo de tempo.

Falha (Sem Vídeo): O veículo viajou por mais de 5 minutos, mas a câmera não gravou nada.

Falso Alarme: A câmera gerou um alerta de ignição, mas não houve viagem na Geotab.

Como resultado, o sistema calcula uma nota de acertividade para cada placa, filtrando alertas duplicados e ignorando manobras muito curtas (menores que 5 minutos). Além da planilha final detalhada, ele gera um mapa interativo que mostra visualmente onde cada viagem começou e onde ocorreram as falhas.